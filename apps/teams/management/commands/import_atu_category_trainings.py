from datetime import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.clubs.models import Club
from apps.teams.models import Category, CategoryTraining, TrainingLocation


LOCATIONS = {
    "jedlikova": {
        "name": "Jedlíkova 7",
        "address": "Jedlíkova 7, Košice",
        "latitude": "48.6981488",
        "longitude": "21.2339038",
        "order": 1,
    },
    "ostrovskeho": {
        "name": "SOŠ Ostrovského",
        "address": "Ostrovského, Košice",
        "latitude": "48.7038429",
        "longitude": "21.2505156",
        "order": 2,
    },
}

TRAININGS = {
    "starsi-ziaci": [
        (2, time(17, 0), "ostrovskeho"),
        (3, time(17, 0), "ostrovskeho"),
        (4, time(15, 0), "jedlikova"),
    ],
    "pripravka": [
        (2, time(15, 0), "jedlikova"),
        (5, time(15, 0), "jedlikova"),
    ],
    "mladsi-ziaci": [
        (1, time(15, 0), "jedlikova"),
        (3, time(15, 0), "jedlikova"),
    ],
    "dorast": [
        (2, time(18, 30), "ostrovskeho"),
        (3, time(18, 30), "ostrovskeho"),
        (4, time(16, 30), "jedlikova"),
    ],
}


class Command(BaseCommand):
    help = "Vytvorí spoločné tréningové miesta a importuje tréningy kategórií ATU."

    def add_arguments(self, parser):
        parser.add_argument("--club", default="atu-kosice")

    @transaction.atomic
    def handle(self, *args, **options):
        club_slug = options["club"]

        try:
            club = Club.objects.get(slug=club_slug)
        except Club.DoesNotExist as exc:
            raise CommandError(f"Klub so slugom '{club_slug}' neexistuje.") from exc

        locations = {}
        for key, data in LOCATIONS.items():
            location, created = TrainingLocation.objects.update_or_create(
                club=club,
                name=data["name"],
                defaults={
                    "address": data["address"],
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "order": data["order"],
                    "is_active": True,
                },
            )
            locations[key] = location
            self.stdout.write(f"{'Vytvorené' if created else 'Aktualizované'} miesto: {location.name}")

        imported = 0
        for slug, slots in TRAININGS.items():
            category = (
                Category.objects.filter(club=club, slug=slug)
                .order_by("-season", "id")
                .first()
            )
            if not category:
                self.stdout.write(self.style.WARNING(f"Kategória '{slug}' nebola nájdená, preskakujem."))
                continue

            for order, (weekday, start_time, location_key) in enumerate(slots, start=1):
                training, created = CategoryTraining.objects.update_or_create(
                    category=category,
                    weekday=weekday,
                    start_time=start_time,
                    location=locations[location_key],
                    defaults={"order": order, "is_active": True},
                )
                imported += 1
                self.stdout.write(
                    f"{'Vytvorený' if created else 'Aktualizovaný'}: "
                    f"{category.name} – {training.get_weekday_display()} {start_time.strftime('%H:%M')}"
                )

        self.stdout.write(self.style.SUCCESS(f"Hotovo. Spracovaných tréningov: {imported}."))
