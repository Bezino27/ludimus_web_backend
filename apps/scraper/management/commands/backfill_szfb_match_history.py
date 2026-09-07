from types import SimpleNamespace

from django.core.management.base import BaseCommand, CommandError

from apps.scraper.models import SzfbTeamWatch
from apps.scraper.services.szfb_match_history import (
    get_match_history_for_watch,
    persist_finished_match_history,
)
from apps.scraper.services.szfb_scraper import (
    fetch_matches,
    filter_matches_for_team,
)


class Command(BaseCommand):
    help = "Jednorazovo doplní posledné finished SZFB zápasy do SzfbMatchHistory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch-id",
            type=int,
            required=True,
            help="ID aktuálneho SzfbTeamWatch. Používa sa iba pre klub a identitu tímu.",
        )
        parser.add_argument(
            "--results-url",
            required=True,
            help="Results URL starej SZFB súťaže.",
        )
        parser.add_argument(
            "--competition-id",
            type=int,
            required=True,
            help="Staré SZFB competition ID.",
        )
        parser.add_argument(
            "--competition-name",
            required=True,
            help="Názov starej súťaže.",
        )
        parser.add_argument(
            "--season",
            required=True,
            help="Sezóna starej súťaže, napr. 2025/2026.",
        )

    def handle(self, *args, **options):
        watch_id = options["watch_id"]
        results_url = options["results_url"]
        competition_id = options["competition_id"]
        competition_name = options["competition_name"]
        season = options["season"]

        try:
            current_watch = (
                SzfbTeamWatch.objects
                .select_related("club", "competition")
                .get(id=watch_id)
            )
        except SzfbTeamWatch.DoesNotExist as exc:
            raise CommandError(
                f"SzfbTeamWatch s ID {watch_id} neexistuje."
            ) from exc

        if not current_watch.club_id:
            raise CommandError(
                "Zvolený watch nemá priradený klub."
            )

        self.stdout.write(
            f"Načítavam starú súťaž pre: {current_watch.label}"
        )
        self.stdout.write(
            f"Tím: {current_watch.team_name}"
        )
        self.stdout.write(
            f"URL: {results_url}"
        )

        all_matches = fetch_matches(results_url)

        self.stdout.write(
            f"Scraper načítal {len(all_matches)} zápasov."
        )

        filtered_matches = filter_matches_for_team(
            matches=all_matches,
            team_name=current_watch.team_name,
        )

        finished_matches = [
            match
            for match in filtered_matches
            if match.get("match_type") == "finished"
        ]

        self.stdout.write(
            f"Pre tím bolo nájdených {len(filtered_matches)} zápasov, "
            f"z toho {len(finished_matches)} finished."
        )

        # Helper používa watch.competition iba ako metadata.
        # Preto vytvoríme dočasný objekt so starými competition údajmi.
        old_competition = SimpleNamespace(
            szfb_competition_id=competition_id,
            name=competition_name,
            season=season,
        )

        history_watch = SimpleNamespace(
            club_id=current_watch.club_id,
            label=current_watch.label,
            team_name=current_watch.team_name,
            competitor_id=current_watch.competitor_id,
            competition=old_competition,
        )

        persist_finished_match_history(
            history_watch,
            filtered_matches,
        )

        history = list(
            get_match_history_for_watch(history_watch)
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill dokončený. History obsahuje {len(history)} zápasov."
            )
        )

        for match in history:
            time_text = (
                match.match_time.strftime("%H:%M")
                if match.match_time
                else "--:--"
            )

            self.stdout.write(
                f"- {match.match_date} {time_text} | "
                f"{match.team_name} vs {match.opponent} | "
                f"{match.result}"
            )
