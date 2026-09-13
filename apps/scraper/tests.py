from unittest.mock import patch
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from io import StringIO

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clubs.models import Club, ClubMembership
from apps.scraper.models import (
    ClubPlayer,
    SzfbCompetition,
    SzfbGoalieStat,
    SzfbMatch,
    SzfbMatchHistory,
    SzfbPlayerStat,
    SzfbStandingRow,
    SzfbTeamWatch,
    SzfbWatchAutoSyncConfig,
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
    run_watch_sync,
)
from apps.scraper.services.szfb_scraper import (
    SzfbPlayerStatsParseError,
    build_team_player_stats_url,
    classify_match_type,
    parse_team_player_stats_html,
)
from apps.scraper.services.szfb_sync import sync_competition_from_home_url
from apps.scraper.services.szfb_sync import (
    _upsert_goalie_stats,
    _upsert_player_stats,
)
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


class SzfbTeamPlayerStatsParserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixture_path = Path(__file__).with_name("test_fixtures") / "team_player_stats.html"
        cls.html = fixture_path.read_text(encoding="utf-8")

    def test_builds_real_team_player_stats_url(self):
        self.assertEqual(
            build_team_player_stats_url(
                1241,
                "Florbalová extraliga mužov",
                670596,
                "FaBK ATU Košice",
            ),
            "https://www.szfb.sk/sk/stats/teams/1241/"
            "florbalova-extraliga-muzov/team/670596/"
            "fabk-atu-kosice/PlayerStats",
        )

    def test_parses_scoring_zero_point_and_zero_game_players(self):
        result = parse_team_player_stats_html(self.html)

        self.assertEqual(len(result["players"]), 3)
        self.assertEqual(result["players"][0]["points"], 1)
        self.assertEqual(result["players"][1]["points"], 0)
        self.assertEqual(result["players"][2]["games"], 0)
        self.assertEqual(result["players"][2]["points"], 0)

    def test_parses_player_id_and_empty_cells(self):
        result = parse_team_player_stats_html(self.html)

        self.assertEqual(result["players"][0]["szfb_player_id"], 887600)
        self.assertEqual(result["players"][2]["szfb_player_id"], 999001)
        self.assertIsNone(result["players"][2]["birth_year"])
        self.assertIsNone(result["players"][2]["jersey_number"])

    def test_parses_all_goalie_statistics_and_duration(self):
        goalie = parse_team_player_stats_html(self.html)["goalies"][0]

        self.assertEqual(goalie["szfb_player_id"], 885386)
        self.assertEqual(goalie["jersey_number"], 39)
        self.assertEqual(goalie["shots_against"], 44)
        self.assertEqual(goalie["goals_against_average"], Decimal("9.00"))
        self.assertEqual(goalie["save_percentage"], Decimal("79.55"))
        self.assertEqual(goalie["minutes_played_seconds"], 3600)

    def test_valid_empty_tables_are_distinct_from_invalid_html(self):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(self.html, "lxml")
        for tbody in soup.select("table tbody"):
            tbody.clear()

        self.assertEqual(
            parse_team_player_stats_html(str(soup)),
            {"players": [], "goalies": []},
        )
        with self.assertRaises(SzfbPlayerStatsParseError):
            parse_team_player_stats_html("<html><body>changed</body></html>")


class SzfbPlayerStatsSyncTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.competition = SzfbCompetition.objects.create(
            szfb_competition_id=1241,
            name="Florbalová extraliga mužov",
            season="2025/2026",
            source_url="https://example.com/home/1241",
        )
        self.watch = SzfbTeamWatch.objects.create(
            label="Muži",
            competition=self.competition,
            club=self.club,
            team_name="FaBK ATU Košice",
            competitor_id=670596,
        )

    def player_data(self, **overrides):
        data = {
            "szfb_player_id": 887600,
            "rank": 1,
            "jersey_number": 13,
            "player_name": "Matej Kender",
            "birth_year": 2010,
            "team_short_name": "",
            "player_position": "F",
            "games": 1,
            "goals": 1,
            "assists": 0,
            "points": 1,
            "points_avg": Decimal("1.00"),
            "esp": 0,
            "ppp": 0,
            "shp": 0,
            "pim": 0,
        }
        data.update(overrides)
        return data

    def goalie_data(self, **overrides):
        data = {
            "szfb_player_id": 885386,
            "rank": 1,
            "jersey_number": 39,
            "player_name": "Róbert Florián Hamrák",
            "birth_year": 2006,
            "player_position": "G",
            "games": 1,
            "wins": 0,
            "overtime_wins": 0,
            "losses": 1,
            "overtime_losses": 0,
            "shots_against": 44,
            "goals_against": 9,
            "goals_against_average": Decimal("9.00"),
            "saves": 35,
            "save_percentage": Decimal("79.55"),
            "minutes_played_seconds": 3600,
            "shutouts": 0,
        }
        data.update(overrides)
        return data

    def sync_data(self, players=None, goalies=None):
        competition_data = {
            "szfb_competition_id": 1241,
            "name": "Florbalová extraliga mužov",
            "season": "2025/2026",
            "source_url": self.competition.source_url,
            "standings_url": "",
            "results_url": "",
        }
        with (
            patch(
                "apps.scraper.services.szfb_sync.extract_competition_info",
                return_value=competition_data,
            ),
            patch(
                "apps.scraper.services.szfb_sync.fetch_team_player_stats",
                return_value={
                    "players": players if players is not None else [],
                    "goalies": goalies if goalies is not None else [],
                },
            ),
        ):
            return sync_competition_from_home_url(
                self.competition.source_url,
                competition_id=self.competition.id,
            )

    def test_resync_updates_same_player_row_and_preserves_photo(self):
        profile = ClubPlayer.objects.create(
            club=self.club,
            full_name="Matej Kender",
            birth_year=2010,
            photo="players/photos/matej.jpg",
        )
        stat = SzfbPlayerStat.objects.create(
            watched_team=self.watch,
            club_player=profile,
            szfb_player_id=887600,
            rank=1,
            player_name="Matej Kender",
            games=1,
            points=1,
        )

        self.sync_data(players=[self.player_data(games=2, goals=3, points=3)])
        stat.refresh_from_db()
        profile.refresh_from_db()

        self.assertEqual(SzfbPlayerStat.objects.count(), 1)
        self.assertEqual(stat.games, 2)
        self.assertEqual(stat.goals, 3)
        self.assertEqual(stat.pk, SzfbPlayerStat.objects.get().pk)
        self.assertEqual(stat.club_player_id, profile.id)
        self.assertEqual(profile.photo.name, "players/photos/matej.jpg")

    def test_resync_preserves_manual_pairing(self):
        manual_profile = ClubPlayer.objects.create(
            club=self.club,
            full_name="Manuálne opravený profil",
            birth_year=1990,
        )
        stat = SzfbPlayerStat.objects.create(
            watched_team=self.watch,
            club_player=manual_profile,
            szfb_player_id=887600,
            rank=1,
            player_name="Staré meno",
        )

        self.sync_data(players=[self.player_data()])
        stat.refresh_from_db()

        self.assertEqual(stat.club_player_id, manual_profile.id)
        self.assertEqual(ClubPlayer.objects.count(), 1)

    def test_legacy_stat_is_backfilled_without_changing_its_id_or_pairing(self):
        profile = ClubPlayer.objects.create(
            club=self.club,
            full_name="Matej Kender",
            birth_year=2010,
        )
        stat = SzfbPlayerStat.objects.create(
            watched_team=self.watch,
            club_player=profile,
            rank=99,
            player_name="Matej Kender",
            birth_year=2010,
        )

        self.sync_data(players=[self.player_data()])
        stat.refresh_from_db()

        self.assertEqual(stat.szfb_player_id, 887600)
        self.assertEqual(stat.club_player_id, profile.id)
        self.assertEqual(SzfbPlayerStat.objects.get().id, stat.id)

    def test_same_club_player_is_used_in_two_seasons(self):
        _upsert_player_stats(self.watch, [self.player_data()])
        next_competition = SzfbCompetition.objects.create(
            szfb_competition_id=1300,
            name="Florbalová extraliga mužov",
            season="2026/2027",
        )
        next_watch = SzfbTeamWatch.objects.create(
            label="Muži",
            competition=next_competition,
            club=self.club,
            team_name=self.watch.team_name,
            competitor_id=700000,
        )

        _upsert_player_stats(next_watch, [self.player_data(games=5)])

        self.assertEqual(ClubPlayer.objects.count(), 1)
        self.assertEqual(SzfbPlayerStat.objects.count(), 2)
        self.assertEqual(
            set(SzfbPlayerStat.objects.values_list("club_player_id", flat=True)),
            {ClubPlayer.objects.get().id},
        )

    def test_goalie_resync_updates_without_duplicate_and_uses_profile(self):
        _upsert_goalie_stats(self.watch, [self.goalie_data()])
        stat = SzfbGoalieStat.objects.get()
        profile_id = stat.club_player_id

        _upsert_goalie_stats(
            self.watch,
            [self.goalie_data(games=2, saves=50, save_percentage=Decimal("81.25"))],
        )
        stat.refresh_from_db()

        self.assertEqual(SzfbGoalieStat.objects.count(), 1)
        self.assertEqual(stat.games, 2)
        self.assertEqual(stat.saves, 50)
        self.assertEqual(stat.club_player_id, profile_id)
        self.assertIsNotNone(profile_id)

    def test_admin_endpoints_return_zero_point_player_and_goalie(self):
        _upsert_player_stats(
            self.watch,
            [self.player_data(games=0, goals=0, assists=0, points=0)],
        )
        _upsert_goalie_stats(self.watch, [self.goalie_data()])
        user = get_user_model().objects.create_user(
            username="sports-data-admin",
            password="password",
        )
        client = APIClient()
        client.force_authenticate(user)

        players_response = client.get(
            reverse("admin-szfb-watch-players", kwargs={"watch_id": self.watch.id})
        )
        goalies_response = client.get(
            reverse("admin-szfb-watch-goalies", kwargs={"watch_id": self.watch.id})
        )

        self.assertEqual(players_response.status_code, 200)
        self.assertEqual(players_response.data["count"], 1)
        self.assertEqual(players_response.data["results"][0]["points"], 0)
        self.assertEqual(
            players_response.data["results"][0]["szfb_player_id"],
            887600,
        )
        self.assertEqual(goalies_response.status_code, 200)
        self.assertEqual(goalies_response.data["count"], 1)
        self.assertEqual(
            goalies_response.data["results"][0]["szfb_player_id"],
            885386,
        )

    def test_invalid_scrape_does_not_delete_existing_stats(self):
        stat = SzfbPlayerStat.objects.create(
            watched_team=self.watch,
            szfb_player_id=887600,
            rank=1,
            player_name="Matej Kender",
        )
        competition_data = {
            "szfb_competition_id": 1241,
            "name": self.competition.name,
            "season": self.competition.season,
            "source_url": self.competition.source_url,
            "standings_url": "",
            "results_url": "",
        }
        with (
            patch(
                "apps.scraper.services.szfb_sync.extract_competition_info",
                return_value=competition_data,
            ),
            patch(
                "apps.scraper.services.szfb_sync.fetch_team_player_stats",
                side_effect=SzfbPlayerStatsParseError("changed HTML"),
            ),
            self.assertRaises(SzfbPlayerStatsParseError),
        ):
            sync_competition_from_home_url(
                self.competition.source_url,
                competition_id=self.competition.id,
            )

        self.assertTrue(SzfbPlayerStat.objects.filter(id=stat.id).exists())

    def test_persistence_exception_rolls_back_player_changes(self):
        stat = SzfbPlayerStat.objects.create(
            watched_team=self.watch,
            szfb_player_id=887600,
            rank=1,
            player_name="Matej Kender",
            games=1,
        )
        competition_data = {
            "szfb_competition_id": 1241,
            "name": self.competition.name,
            "season": self.competition.season,
            "source_url": self.competition.source_url,
            "standings_url": "",
            "results_url": "",
        }
        with (
            patch(
                "apps.scraper.services.szfb_sync.extract_competition_info",
                return_value=competition_data,
            ),
            patch(
                "apps.scraper.services.szfb_sync.fetch_team_player_stats",
                return_value={"players": [self.player_data(games=9)], "goalies": []},
            ),
            patch(
                "apps.scraper.services.szfb_sync._upsert_goalie_stats",
                side_effect=RuntimeError("DB failure"),
            ),
            self.assertRaises(RuntimeError),
        ):
            sync_competition_from_home_url(
                self.competition.source_url,
                competition_id=self.competition.id,
            )

        stat.refresh_from_db()
        self.competition.refresh_from_db()
        self.assertEqual(stat.games, 1)
        self.assertIsNone(self.competition.last_synced_at)


class SzfbWatchManagementTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.other_club = Club.objects.create(name="Iný klub", slug="iny-klub")
        self.user = get_user_model().objects.create_user("editor", password="test")
        ClubMembership.objects.create(
            user=self.user, club=self.club, role="club_admin", is_active=True
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.competition = SzfbCompetition.objects.create(
            szfb_competition_id=2001,
            name="Extraliga",
            season="2026/2027",
            source_url="https://example.com/competition",
        )
        self.watch = SzfbTeamWatch.objects.create(
            label="Muži",
            competition=self.competition,
            club=self.club,
            team_name="ATU Košice",
            competitor_id=100,
        )

    def test_delete_watch_cascades_only_watch_owned_current_data(self):
        player = ClubPlayer.objects.create(
            club=self.club,
            full_name="Peter Hráč",
            birth_year=1999,
            photo="players/photos/peter.jpg",
        )
        SzfbPlayerStat.objects.create(
            watched_team=self.watch,
            club_player=player,
            szfb_player_id=11,
            rank=1,
            player_name="HRÁČ Peter",
        )
        SzfbGoalieStat.objects.create(
            watched_team=self.watch,
            club_player=player,
            szfb_player_id=12,
            rank=1,
            player_name="BRANKÁR Peter",
        )
        SzfbMatch.objects.create(
            watched_team=self.watch,
            match_type="upcoming",
            opponent="Súper",
            external_key="current-1",
        )
        history = SzfbMatchHistory.objects.create(
            club=self.club,
            team_identity="competitor:100",
            team_label=self.watch.label,
            team_name=self.watch.team_name,
            match_date=timezone.localdate(),
            opponent="Starý súper",
            result="5:2",
            external_key="history-1",
        )
        category = Category.objects.create(
            club=self.club,
            name="Muži",
            slug="muzi-delete",
            season="2026/2027",
            birth_year_from=1990,
            birth_year_to=2010,
            szfb_team_watch=self.watch,
        )
        SzfbWatchAutoSyncConfig.objects.create(watch=self.watch, is_enabled=True)

        response = self.client.delete(
            reverse("admin-szfb-watch-detail", args=[self.watch.id]),
            {"club": self.club.slug},
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(SzfbTeamWatch.objects.filter(id=self.watch.id).exists())
        self.assertEqual(SzfbPlayerStat.objects.count(), 0)
        self.assertEqual(SzfbGoalieStat.objects.count(), 0)
        self.assertEqual(SzfbMatch.objects.count(), 0)
        self.assertEqual(SzfbWatchAutoSyncConfig.objects.count(), 0)
        self.assertTrue(ClubPlayer.objects.filter(id=player.id).exists())
        player.refresh_from_db()
        self.assertEqual(player.photo.name, "players/photos/peter.jpg")
        self.assertTrue(SzfbMatchHistory.objects.filter(id=history.id).exists())
        self.assertTrue(SzfbCompetition.objects.filter(id=self.competition.id).exists())
        category.refresh_from_db()
        self.assertIsNone(category.szfb_team_watch_id)

    def test_delete_foreign_club_watch_is_not_exposed(self):
        foreign_watch = SzfbTeamWatch.objects.create(
            label="Cudzí tím",
            competition=self.competition,
            club=self.other_club,
            team_name="Cudzí klub",
        )
        response = self.client.delete(
            reverse("admin-szfb-watch-detail", args=[foreign_watch.id]),
            {"club": self.other_club.slug},
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SzfbTeamWatch.objects.filter(id=foreign_watch.id).exists())

    def test_auto_sync_get_and_patch_are_watch_scoped(self):
        url = reverse("admin-szfb-watch-auto-sync-config", args=[self.watch.id])
        response = self.client.get(url, {"club": self.club.slug})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["watch_id"], self.watch.id)
        self.assertFalse(response.data["is_enabled"])

        response = self.client.patch(
            url,
            {
                "club_slug": self.club.slug,
                "is_enabled": True,
                "frequency": "weekly",
                "weekday": 5,
                "run_time": "20:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        config = SzfbWatchAutoSyncConfig.objects.get(watch=self.watch)
        self.assertTrue(config.is_enabled)
        self.assertEqual(config.weekday, 5)

    def test_auto_sync_foreign_watch_is_not_exposed(self):
        foreign_watch = SzfbTeamWatch.objects.create(
            label="Cudzí tím",
            competition=self.competition,
            club=self.other_club,
            team_name="Cudzí klub",
        )
        url = reverse("admin-szfb-watch-auto-sync-config", args=[foreign_watch.id])
        self.assertEqual(self.client.get(url, {"club": self.other_club.slug}).status_code, 404)
        self.assertEqual(
            self.client.patch(
                url,
                {"club_slug": self.other_club.slug, "is_enabled": True},
                format="json",
            ).status_code,
            404,
        )

    def test_inactive_watch_cannot_enable_auto_sync(self):
        self.watch.is_active = False
        self.watch.save(update_fields=["is_active"])
        url = reverse("admin-szfb-watch-auto-sync-config", args=[self.watch.id])
        response = self.client.patch(
            url,
            {"club_slug": self.club.slug, "is_enabled": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SzfbWatchAutoSyncConfig.objects.get(watch=self.watch).is_enabled)


class SzfbWatchAutoSyncRunnerTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.competition = SzfbCompetition.objects.create(
            szfb_competition_id=2100,
            name="Spoločná súťaž",
            source_url="https://example.com/competition",
        )
        self.men = SzfbTeamWatch.objects.create(
            label="Muži", competition=self.competition, club=self.club,
            team_name="ATU Muži", competitor_id=1,
        )
        self.juniors = SzfbTeamWatch.objects.create(
            label="Juniori", competition=self.competition, club=self.club,
            team_name="ATU Juniori", competitor_id=2,
        )

    def create_config(self, watch, **kwargs):
        defaults = {
            "is_enabled": True,
            "next_run_at": timezone.now() - timedelta(minutes=1),
        }
        defaults.update(kwargs)
        return SzfbWatchAutoSyncConfig.objects.create(watch=watch, **defaults)

    def test_is_due_requires_enabled_and_active_watch(self):
        config = self.create_config(self.men)
        self.assertTrue(config.is_due())
        config.is_enabled = False
        self.assertFalse(config.is_due())
        config.is_enabled = True
        self.men.is_active = False
        self.men.save(update_fields=["is_active"])
        self.assertFalse(config.is_due())

    @patch("apps.scraper.management.commands.run_due_szfb_syncs.run_watch_sync")
    def test_runner_skips_disabled_and_inactive_watches(self, run_watch_sync_mock):
        self.create_config(self.men, is_enabled=False)
        self.juniors.is_active = False
        self.juniors.save(update_fields=["is_active"])
        self.create_config(self.juniors, is_enabled=True)

        call_command("run_due_szfb_syncs", stdout=StringIO())

        run_watch_sync_mock.assert_not_called()

    @patch("apps.scraper.management.commands.run_due_szfb_syncs.run_watch_sync")
    def test_due_runner_syncs_only_due_watch(self, run_watch_sync_mock):
        men_config = self.create_config(self.men)
        junior_config = self.create_config(
            self.juniors,
            next_run_at=timezone.now() + timedelta(days=1),
        )

        call_command("run_due_szfb_syncs", stdout=StringIO())

        run_watch_sync_mock.assert_called_once_with(self.men.id)
        men_config.refresh_from_db()
        junior_config.refresh_from_db()
        self.assertEqual(men_config.last_status, "success")
        self.assertIsNone(junior_config.last_run_at)

    @patch("apps.scraper.management.commands.run_due_szfb_syncs.run_watch_sync")
    def test_runner_records_error_for_only_failing_watch(self, run_watch_sync_mock):
        config = self.create_config(self.men)
        run_watch_sync_mock.side_effect = RuntimeError("SZFB nedostupné")

        call_command("run_due_szfb_syncs", stdout=StringIO())

        config.refresh_from_db()
        self.assertEqual(config.last_status, "error")
        self.assertIn("Muži", config.last_message)
        self.assertIn("SZFB nedostupné", config.last_message)
        self.assertGreater(config.next_run_at, timezone.now())

    @patch("apps.scraper.services.szfb_sync_runner.sync_competition_from_home_url")
    @patch("apps.scraper.services.szfb_sync_runner.schedule_revalidation")
    def test_automatic_sync_targets_one_watch(
        self, schedule_revalidation_mock, sync_mock
    ):
        sync_mock.return_value = self.competition
        run_watch_sync(self.men.id)
        sync_mock.assert_called_once_with(
            self.competition.source_url,
            competition_id=self.competition.id,
            watch_ids=[self.men.id],
        )

    @patch("apps.scraper.services.szfb_sync_runner.sync_competition_from_home_url")
    def test_manual_competition_sync_keeps_all_watches_scope(self, sync_mock):
        sync_mock.return_value = self.competition
        run_competition_sync(self.competition.id)
        sync_mock.assert_called_once_with(
            self.competition.source_url,
            competition_id=self.competition.id,
        )

    def test_two_watches_have_independent_schedules(self):
        men_config = self.create_config(self.men, weekday=0)
        junior_config = self.create_config(self.juniors, weekday=5)
        self.assertNotEqual(men_config.watch_id, junior_config.watch_id)
        self.assertEqual(SzfbWatchAutoSyncConfig.objects.count(), 2)
        self.assertNotEqual(
            men_config.calculate_next_run_at(),
            junior_config.calculate_next_run_at(),
        )

    def test_next_run_at_uses_configured_weekday_and_time(self):
        config = self.create_config(self.men, weekday=0, run_time="06:00")
        sunday_noon = timezone.make_aware(datetime(2026, 9, 13, 12, 0))
        next_run = timezone.localtime(
            config.calculate_next_run_at(from_datetime=sunday_noon)
        )
        self.assertEqual(next_run, timezone.make_aware(datetime(2026, 9, 14, 6, 0)))

    def test_shared_sync_filters_remote_player_fetches_by_watch_ids(self):
        competition_data = {
            "szfb_competition_id": self.competition.szfb_competition_id,
            "name": self.competition.name,
            "season": self.competition.season,
            "source_url": self.competition.source_url,
            "standings_url": "",
            "results_url": "",
        }
        with (
            patch(
                "apps.scraper.services.szfb_sync.extract_competition_info",
                return_value=competition_data,
            ),
            patch(
                "apps.scraper.services.szfb_sync.fetch_team_player_stats",
                return_value={"players": [], "goalies": []},
            ) as fetch_stats,
        ):
            sync_competition_from_home_url(
                self.competition.source_url,
                competition_id=self.competition.id,
                watch_ids=[self.men.id],
            )
            self.assertEqual(fetch_stats.call_count, 1)

            fetch_stats.reset_mock()
            sync_competition_from_home_url(
                self.competition.source_url,
                competition_id=self.competition.id,
            )
            self.assertEqual(fetch_stats.call_count, 2)
