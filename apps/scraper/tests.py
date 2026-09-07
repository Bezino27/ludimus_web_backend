from unittest.mock import patch
from datetime import timedelta

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
    SzfbMatch,
    SzfbMatchHistory,
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
from apps.scraper.services.szfb_scraper import classify_match_type
from apps.scraper.services.szfb_sync import sync_competition_from_home_url
from apps.scraper.services.szfb_match_history import (
    get_match_history_for_watch,
    persist_finished_match_history,
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


class SzfbMatchClassificationTests(TestCase):
    def test_colon_is_upcoming(self):
        self.assertEqual(classify_match_type(":"), "upcoming")

    def test_empty_result_is_upcoming(self):
        self.assertEqual(classify_match_type(""), "upcoming")

    def test_real_score_is_finished(self):
        self.assertEqual(classify_match_type("5:3"), "finished")

    def test_spaced_colon_is_upcoming(self):
        self.assertEqual(classify_match_type(" : "), "upcoming")


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


class SzfbMatchHistoryTests(SzfbRevalidationTestMixin, TestCase):
    def match_data(self, index=0, match_type="finished", result="5:3"):
        return {
            "match_type": match_type,
            "match_date": timezone.localdate() - timedelta(days=index),
            "match_time": None,
            "opponent": f"Súper {index}",
            "venue": "Hala",
            "result": result,
            "is_home": True,
            "external_key": f"match-{index}",
        }

    def test_finished_match_is_saved_and_upcoming_is_not(self):
        persist_finished_match_history(
            self.watch,
            [self.match_data(), self.match_data(1, match_type="upcoming", result=":")],
        )

        self.assertEqual(SzfbMatchHistory.objects.count(), 1)
        self.assertEqual(SzfbMatchHistory.objects.get().opponent, "Súper 0")

    def test_repeated_persistence_updates_without_duplicate(self):
        match = self.match_data()
        persist_finished_match_history(self.watch, [match])
        match["venue"] = "Nová hala"
        persist_finished_match_history(self.watch, [match])

        self.assertEqual(SzfbMatchHistory.objects.count(), 1)
        self.assertEqual(SzfbMatchHistory.objects.get().venue, "Nová hala")

    def test_six_finished_matches_are_pruned_to_latest_five(self):
        persist_finished_match_history(
            self.watch,
            [self.match_data(index) for index in range(6)],
        )

        history = list(get_match_history_for_watch(self.watch))
        self.assertEqual(len(history), 5)
        self.assertEqual([item.opponent for item in history], [f"Súper {i}" for i in range(5)])

    def test_new_season_watch_uses_same_history(self):
        persist_finished_match_history(self.watch, [self.match_data(1)])
        new_competition = SzfbCompetition.objects.create(
            szfb_competition_id=1242,
            name="Extraliga 2026/27",
            season="2026/2027",
        )
        new_watch = SzfbTeamWatch.objects.create(
            label=self.watch.label,
            competition=new_competition,
            club=self.club,
            team_name="FaBK ATU Košice nový názov",
            competitor_id=999,
        )
        persist_finished_match_history(new_watch, [self.match_data(0)])

        self.assertEqual(get_match_history_for_watch(new_watch).count(), 2)

    def test_deleting_watch_does_not_delete_history(self):
        persist_finished_match_history(self.watch, [self.match_data()])
        self.watch.delete()

        self.assertEqual(SzfbMatchHistory.objects.count(), 1)

    @patch("apps.scraper.services.szfb_sync.fetch_matches")
    @patch("apps.scraper.services.szfb_sync.extract_competition_info")
    def test_normal_sync_persists_finished_match(
        self,
        extract_competition_info,
        fetch_matches,
    ):
        self.watch.competitor_id = None
        self.watch.save(update_fields=["competitor_id"])
        extract_competition_info.return_value = {
            "szfb_competition_id": self.competition.szfb_competition_id,
            "name": self.competition.name,
            "season": "2026/2027",
            "source_url": self.competition.source_url,
            "standings_url": "",
            "results_url": "https://example.com/results",
        }
        fetch_matches.return_value = [
            {
                "match_type": "finished",
                "match_date": timezone.localdate(),
                "match_time": None,
                "team1": self.watch.team_name,
                "team2": "Súper",
                "venue": "Hala",
                "result": "5:3",
            }
        ]

        sync_competition_from_home_url(
            self.competition.source_url,
            competition_id=self.competition.id,
        )

        self.assertEqual(SzfbMatchHistory.objects.count(), 1)


class SzfbDashboardHistoricalResultsTests(SzfbRevalidationTestMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.create_category("muzi")
        self.user = get_user_model().objects.create_user(
            username="editor-dashboard",
            password="password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_current_watch_returns_four_finished_matches_from_older_watch(self):
        self.assertFalse(
            self.watch.matches.filter(match_type="finished").exists()
        )
        today = timezone.localdate()
        matches = []
        for index in range(4):
            matches.append(
                {
                    "match_type": "finished",
                    "match_date": today - timedelta(days=index + 1),
                    "opponent": f"Súper {index}",
                    "result": "5:3",
                    "external_key": f"old-{index}",
                }
            )
        persist_finished_match_history(self.watch, matches)

        response = APIClient().get(
            reverse("szfb-watch-dashboard", kwargs={"watch_id": self.watch.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["opponent"] for item in response.data["results"]],
            [f"Súper {index}" for index in range(4)],
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
