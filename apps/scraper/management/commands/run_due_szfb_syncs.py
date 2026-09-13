import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.scraper.models import SzfbWatchAutoSyncConfig
from apps.scraper.services.szfb_sync_runner import (
    expire_stale_running_competition_syncs,
    run_watch_sync,
)


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Spustí automatické SZFB synchronizácie tímov, ktoré sú naplánované."

    def add_arguments(self, parser):
        parser.add_argument("--club", type=str, default="")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        expire_stale_running_competition_syncs()
        configs = (
            SzfbWatchAutoSyncConfig.objects.select_related(
                "watch", "watch__club", "watch__competition"
            )
            .filter(is_enabled=True, watch__is_active=True)
            .order_by("watch__club__name", "watch__label")
        )
        if options["club"]:
            configs = configs.filter(watch__club__slug=options["club"])

        if not configs.exists():
            self.stdout.write(self.style.WARNING("Nie je zapnutá žiadna SZFB automatika."))
            return

        for config in configs:
            self.process_config(
                config, now, force=options["force"], dry_run=options["dry_run"]
            )

    def process_config(self, config, now, force=False, dry_run=False):
        watch = config.watch
        label = f"{watch.club} / {watch.label}"
        if not config.next_run_at:
            config.refresh_next_run_at(from_datetime=now)

        if not force and not config.is_due(now):
            self.stdout.write(
                f"{label}: ešte nie je čas. Najbližší sync: {config.next_run_at}"
            )
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY RUN] {label}: spustil by sa sync."))
            return

        try:
            run_watch_sync(watch.id)
        except Exception as exc:
            logger.exception("SZFB watch auto sync failed watch_id=%s", watch.id)
            status = SzfbWatchAutoSyncConfig.STATUS_ERROR
            message = f"{label}: {str(exc)[:4500]}"
            output = self.style.ERROR
        else:
            status = SzfbWatchAutoSyncConfig.STATUS_SUCCESS
            message = f"{label}: synchronizácia bola úspešne dokončená."
            output = self.style.SUCCESS

        config.last_run_at = now
        config.last_status = status
        config.last_message = message
        config.next_run_at = config.calculate_next_run_at(from_datetime=timezone.now())
        config.save(
            update_fields=[
                "last_run_at", "last_status", "last_message", "next_run_at", "updated_at"
            ]
        )
        self.stdout.write(output(message))
