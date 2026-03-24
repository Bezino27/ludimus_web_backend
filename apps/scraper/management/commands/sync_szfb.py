from django.core.management.base import BaseCommand, CommandError

from apps.scraper.services.szfb_sync import sync_competition_from_home_url


class Command(BaseCommand):
    help = "Načíta SZFB súťaž z home URL, uloží tabuľku a zápasy pre sledované tímy."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, type=str)

    def handle(self, *args, **options):
        url = options["url"]

        try:
            competition = sync_competition_from_home_url(url)
        except Exception as exc:
            raise CommandError(f"Sync zlyhal: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Hotovo. Súťaž: {competition.name} ({competition.season})"
            )
        )