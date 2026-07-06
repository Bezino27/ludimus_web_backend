import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.scraper.models import (
    SzfbAutoSyncConfig,
    SzfbCompetition,
)
from apps.scraper.services.szfb_sync_runner import (
    can_start_competition_sync,
    expire_stale_running_competition_syncs,
    run_competition_sync,
)


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Spustí automatické SZFB synchronizácie, ktoré sú práve naplánované."

    def add_arguments(self, parser):
        parser.add_argument(
            "--club",
            type=str,
            default="",
            help="Voliteľný slug klubu, napríklad atu-kosice.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Spustí sync bez kontroly next_run_at, ale stále rešpektuje rate-limit.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Iba vypíše, čo by sa spustilo, ale nič nespustí.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        club_slug = options["club"]
        force = options["force"]
        dry_run = options["dry_run"]

        expire_stale_running_competition_syncs()

        configs = (
            SzfbAutoSyncConfig.objects
            .select_related("club")
            .filter(is_enabled=True)
            .order_by("club__name")
        )

        if club_slug:
            configs = configs.filter(club__slug=club_slug)

        if not configs.exists():
            self.stdout.write(
                self.style.WARNING("Nie je zapnutá žiadna SZFB automatika.")
            )
            return

        for config in configs:
            self.process_config(
                config=config,
                now=now,
                force=force,
                dry_run=dry_run,
            )

    def process_config(self, config, now, force=False, dry_run=False):
        club = config.club

        if not config.next_run_at:
            config.refresh_next_run_at(from_datetime=now)
            self.stdout.write(
                f"{club}: doplnený najbližší sync na {config.next_run_at}."
            )

        is_due = config.is_due(now)

        if not force and not is_due:
            self.stdout.write(
                f"{club}: ešte nie je čas. Najbližší sync: {config.next_run_at}"
            )
            return

        competitions = (
            SzfbCompetition.objects
            .filter(
                watched_teams__club=club,
                watched_teams__is_active=True,
            )
            .distinct()
            .order_by("name")
        )

        total_count = competitions.count()

        if total_count == 0:
            message = "Klub nemá žiadne aktívne SZFB súťaže na synchronizáciu."
            self.finish_config(
                config=config,
                status=SzfbAutoSyncConfig.STATUS_SKIPPED,
                message=message,
                now=now,
                dry_run=dry_run,
            )
            self.stdout.write(self.style.WARNING(f"{club}: {message}"))
            return

        self.stdout.write(
            self.style.NOTICE(
                f"{club}: nájdených {total_count} súťaží na kontrolu."
            )
        )

        if dry_run:
            for competition in competitions:
                self.stdout.write(
                    f"[DRY RUN] {club}: sync súťaže {competition.id} "
                    f"{competition.name}"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY RUN] {club}: hotovo, nič nebolo spustené."
                )
            )
            return

        started_count = 0
        skipped_count = 0
        error_count = 0
        messages = []

        for competition in competitions:
            can_start, reason, next_allowed_at = can_start_competition_sync(
                competition,
            )

            if not can_start:
                skipped_count += 1
                message = (
                    f"Preskočené: {competition.name} "
                    f"reason={reason} next_allowed_at={next_allowed_at}"
                )
                messages.append(message)
                self.stdout.write(self.style.WARNING(message))
                continue

            started_count += 1

            SzfbCompetition.objects.filter(id=competition.id).update(
                sync_status=SzfbCompetition.SYNC_STATUS_RUNNING,
                sync_started_at=timezone.now(),
                sync_last_attempt_at=timezone.now(),
                sync_finished_at=None,
                sync_error="",
            )

            self.stdout.write(
                self.style.NOTICE(
                    f"Spúšťam SZFB sync: {competition.id} {competition.name}"
                )
            )

            run_competition_sync(competition.id)

            competition.refresh_from_db()

            if competition.sync_status == SzfbCompetition.SYNC_STATUS_ERROR:
                error_count += 1
                messages.append(
                    f"Chyba: {competition.name}: {competition.sync_error}"
                )
            else:
                messages.append(f"Hotovo: {competition.name}")

        if error_count:
            status = SzfbAutoSyncConfig.STATUS_ERROR
        elif started_count:
            status = SzfbAutoSyncConfig.STATUS_SUCCESS
        else:
            status = SzfbAutoSyncConfig.STATUS_SKIPPED

        final_message = (
            f"Spustené: {started_count}, "
            f"preskočené: {skipped_count}, "
            f"chyby: {error_count}. "
            + " | ".join(messages[:10])
        )

        self.finish_config(
            config=config,
            status=status,
            message=final_message,
            now=now,
            dry_run=False,
        )

        if status == SzfbAutoSyncConfig.STATUS_ERROR:
            self.stdout.write(self.style.ERROR(f"{club}: {final_message}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"{club}: {final_message}"))

    def finish_config(self, config, status, message, now, dry_run=False):
        if dry_run:
            return

        config.last_run_at = now
        config.last_status = status
        config.last_message = message[:5000]
        config.next_run_at = config.calculate_next_run_at(from_datetime=timezone.now())
        config.save(
            update_fields=[
                "last_run_at",
                "last_status",
                "last_message",
                "next_run_at",
                "updated_at",
            ]
        )