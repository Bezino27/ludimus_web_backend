from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clubs.models import Club
from apps.scraper.models import (
    ClubPlayer,
    SzfbCompetition,
    SzfbPlayerStat,
    SzfbStandingRow,
    SzfbTeamWatch,
)
from apps.scraper.revalidation import (
    get_competition_revalidation_paths,
    get_player_revalidation_paths,
    get_watch_revalidation_paths,
)
from apps.scraper.admin import ClubPlayerAdmin
from apps.scraper.services.szfb_sync_runner import (
    can_start_competition_sync,
    run_competition_sync,
)
from apps.teams.models import Category


class SzfbRevalidationTestMixin:
    def setUp(self):
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.competition = SzfbCompetition.objects.create(
            szfb_competition_id=1241,
            name="Extraliga",
            source_url="https://example.com/competition",
        )
        self.watch = SzfbTeamWatch.objects.create(
            label="Muži",
            competition=self.competition,
            club=self.club,
            team_name="ATU Košice",
            competitor_id=1,
        )
        self.player = ClubPlayer.objects.create(
            club=self.club,
            full_name="Peter Bezeg",
            birth_year=1995,
        )
        self.stat = SzfbPlayerStat.objects.create(
            watched_team=self.watch,
            club_player=self.player,
            rank=1,
            player_name="BEZEG Peter",
        )

    def create_category(self, slug, watch=None):
        return Category.objects.create(
            club=self.club,
            name=slug.title(),
            slug=slug,
            season="2025/2026",
            birth_year_from=1990,
            birth_year_to=2010,
            szfb_team_watch=watch or self.watch,
        )


class SzfbStandingRowConstraintTests(TestCase):
    def setUp(self):
        self.competition = SzfbCompetition.objects.create(
            szfb_competition_id=999,
            name="Juniorská liga",
        )

    def test_different_teams_can_share_position_in_one_competition(self):
        SzfbStandingRow.objects.create(
            competition=self.competition, position=2, team_name="Tím A"
        )
        SzfbStandingRow.objects.create(
            competition=self.competition, position=2, team_name="Tím B"
        )

        self.assertEqual(self.competition.standings.filter(position=2).count(), 2)

    def test_team_name_must_be_unique_within_competition(self):
        SzfbStandingRow.objects.create(
            competition=self.competition, position=2, team_name="Tím A"
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            SzfbStandingRow.objects.create(
                competition=self.competition, position=3, team_name="Tím A"
            )


class SzfbSyncStartGuardTests(TestCase):
    def setUp(self):
        self.competition = SzfbCompetition.objects.create(
            szfb_competition_id=1000,
            name="Extraliga",
            source_url="https://example.com/competition",
        )

    def test_recent_successful_sync_is_rate_limited_without_user(self):
        self.competition.last_synced_at = timezone.now()
        self.competition.save(update_fields=["last_synced_at"])

        can_start, reason, next_allowed_at = can_start_competition_sync(
            self.competition
        )
        self.assertFalse(can_start)
        self.assertEqual(reason, "rate_limited")
        self.assertIsNotNone(next_allowed_at)

    def test_only_exact_username_and_email_can_bypass_rate_limit(self):
        self.competition.last_synced_at = timezone.now()
        self.competition.save(update_fields=["last_synced_at"])
        user_model = get_user_model()
        exact_user = user_model(
            username="guli", email="guli@ludimus.sk"
        )
        username_only = user_model(
            username="guli", email="other@ludimus.sk"
        )
        email_only = user_model(
            username="other", email="guli@ludimus.sk"
        )

        self.assertEqual(
            can_start_competition_sync(self.competition, user=exact_user),
            (True, "", None),
        )
        self.assertEqual(
            can_start_competition_sync(self.competition, user=username_only)[1],
            "rate_limited",
        )
        self.assertEqual(
            can_start_competition_sync(self.competition, user=email_only)[1],
            "rate_limited",
        )

    def test_running_sync_is_still_blocked(self):
        user = get_user_model()(username="guli", email="guli@ludimus.sk")
        self.competition.sync_status = SzfbCompetition.SYNC_STATUS_RUNNING
        self.competition.sync_started_at = timezone.now()

        self.assertEqual(
            can_start_competition_sync(self.competition, user=user),
            (False, "already_running", None),
        )

    def test_bypass_user_is_still_blocked_without_source_url(self):
        user = get_user_model()(username="guli", email="guli@ludimus.sk")
        self.competition.source_url = ""

        self.assertEqual(
            can_start_competition_sync(self.competition, user=user),
            (False, "missing_source_url", None),
        )


class SzfbRevalidationPathTests(SzfbRevalidationTestMixin, TestCase):
    def test_player_paths_are_unique_and_derived_from_linked_categories(self):
        self.create_category("muzi")
        self.create_category("seniori")

        self.assertEqual(
            get_player_revalidation_paths(self.player),
            ["/kategorie/muzi", "/kategorie/seniori"],
        )

    def test_competition_paths_use_active_watches_and_include_home_for_muzi(self):
        self.create_category("muzi")
        self.create_category("seniori")
        inactive_watch = SzfbTeamWatch.objects.create(
            label="Inactive",
            competition=self.competition,
            club=self.club,
            team_name="Inactive",
            is_active=False,
        )
        self.create_category("inactive", watch=inactive_watch)

        self.assertEqual(
            get_competition_revalidation_paths(self.competition),
            ["/", "/kategorie/muzi", "/kategorie/seniori"],
        )

    def test_watch_paths_include_linked_categories_and_home_when_needed(self):
        self.create_category("muzi")
        self.create_category("seniori")
        self.assertEqual(
            get_watch_revalidation_paths(self.watch),
            ["/", "/kategorie/muzi", "/kategorie/seniori"],
        )

    @patch("apps.scraper.admin.schedule_revalidation")
    def test_club_player_django_admin_schedules_revalidation(self, schedule_revalidation):
        self.create_category("muzi")
        ClubPlayerAdmin(ClubPlayer, admin.site).save_model(None, self.player, None, True)
        schedule_revalidation.assert_called_once_with(
            ["/kategorie/muzi"],
            reason="Club player saved in Django admin",
            club_slug="atu-kosice",
        )


class SzfbAdminRevalidationTests(SzfbRevalidationTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.create_category("muzi")
        self.user = get_user_model().objects.create_user(
            username="editor",
            password="password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("apps.scraper.views.Thread")
    def test_admin_can_start_sync_immediately_after_successful_sync(self, thread):
        self.user.username = "guli"
        self.user.email = "guli@ludimus.sk"
        self.user.save(update_fields=["username", "email"])
        self.competition.last_synced_at = timezone.now()
        self.competition.save(update_fields=["last_synced_at"])

        response = self.client.post(
            reverse(
                "admin-szfb-competition-sync",
                kwargs={"competition_id": self.competition.id},
            )
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "started")
        thread.return_value.start.assert_called_once()

    @patch("apps.scraper.views.schedule_revalidation")
    def test_club_player_update_schedules_revalidation(self, schedule_revalidation):
        response = self.client.patch(
            reverse(
                "admin-szfb-club-player-update",
                kwargs={"player_id": self.player.id},
            ),
            {"bio": "Updated"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        schedule_revalidation.assert_called_once_with(
            ["/kategorie/muzi"],
            reason="ClubPlayer updated via admin API",
            club_slug="atu-kosice",
        )

    @patch("apps.scraper.views.schedule_revalidation")
    def test_player_stat_update_schedules_revalidation(self, schedule_revalidation):
        response = self.client.patch(
            reverse(
                "admin-szfb-player-update",
                kwargs={"player_id": self.stat.id},
            ),
            {"bio": "Updated"},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        schedule_revalidation.assert_called_once_with(
            ["/kategorie/muzi"],
            reason="SZFB player updated via admin API",
            club_slug="atu-kosice",
        )

    @patch("apps.scraper.views.schedule_revalidation")
    def test_watch_update_schedules_revalidation(self, schedule_revalidation):
        response = self.client.patch(
            reverse("admin-szfb-watch-settings-update", kwargs={"watch_id": self.watch.id}),
            {
                "club_slug": self.club.slug,
                "szfb_competition_id": self.competition.szfb_competition_id,
                "competition_name": self.competition.name,
                "competition_season": self.competition.season,
                "competition_source_url": self.competition.source_url,
                "label": "Muži updated",
                "team_name": self.watch.team_name,
                "competitor_id": self.watch.competitor_id,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        schedule_revalidation.assert_called_once_with(
            ["/", "/kategorie/muzi", "/", "/kategorie/muzi"],
            reason="SZFB team watch updated via admin API",
            club_slug="atu-kosice",
        )


class SzfbSyncRevalidationTests(SzfbRevalidationTestMixin, TestCase):
    @patch("apps.scraper.services.szfb_sync_runner.schedule_revalidation")
    @patch("apps.scraper.services.szfb_sync_runner.sync_competition_from_home_url")
    def test_successful_sync_schedules_revalidation(
        self,
        sync_competition_from_home_url,
        schedule_revalidation,
    ):
        self.create_category("muzi")
        sync_competition_from_home_url.return_value = self.competition

        run_competition_sync(self.competition.id)

        schedule_revalidation.assert_called_once_with(
            ["/", "/kategorie/muzi"],
            reason="SZFB competition sync completed",
            club_slug="atu-kosice",
        )
