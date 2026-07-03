from django.core.management.base import BaseCommand

from apps.clubs.models import Club
from apps.scraper.models import (
    ClubPlayer,
    SzfbPlayerStat,
    build_club_player_identity_key,
    normalize_player_name,
)


class Command(BaseCommand):
    help = "Vytvorí ClubPlayer z existujúcich SzfbPlayerStat a prepojí ich."

    def handle(self, *args, **options):
        fallback_club = Club.objects.filter(slug="atu-kosice").first()

        stats = (
            SzfbPlayerStat.objects
            .select_related("watched_team", "watched_team__club", "club_player")
            .all()
        )

        created_count = 0
        linked_count = 0
        skipped_count = 0

        for stat in stats:
            if stat.club_player_id:
                linked_count += 1
                continue

            club = stat.watched_team.club if stat.watched_team else None

            if not club:
                club = fallback_club

            if not club:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Preskakujem hráča bez klubu: {stat.player_name}"
                    )
                )
                continue

            normalized_name = normalize_player_name(stat.player_name)
            identity_key = build_club_player_identity_key(
                stat.player_name,
                stat.birth_year,
            )

            club_player, created = ClubPlayer.objects.get_or_create(
                club=club,
                identity_key=identity_key,
                defaults={
                    "full_name": stat.player_name,
                    "normalized_name": normalized_name,
                    "birth_year": stat.birth_year,
                    "photo": stat.photo.name if stat.photo else "",
                    "jersey_number": stat.jersey_number,
                    "position": stat.player_position or "",
                    "bio": stat.bio or "",
                    "is_active": stat.is_active,
                    "is_featured": stat.is_featured,
                    "display_order": stat.display_order,
                },
            )

            if created:
                created_count += 1
            else:
                changed_fields = []

                if not club_player.full_name and stat.player_name:
                    club_player.full_name = stat.player_name
                    changed_fields.append("full_name")

                if not club_player.normalized_name:
                    club_player.normalized_name = normalized_name
                    changed_fields.append("normalized_name")

                if not club_player.birth_year and stat.birth_year:
                    club_player.birth_year = stat.birth_year
                    changed_fields.append("birth_year")

                if not club_player.photo and stat.photo:
                    club_player.photo = stat.photo.name
                    changed_fields.append("photo")

                if club_player.jersey_number is None and stat.jersey_number is not None:
                    club_player.jersey_number = stat.jersey_number
                    changed_fields.append("jersey_number")

                if not club_player.position and stat.player_position:
                    club_player.position = stat.player_position
                    changed_fields.append("position")

                if not club_player.bio and stat.bio:
                    club_player.bio = stat.bio
                    changed_fields.append("bio")

                if stat.is_featured and not club_player.is_featured:
                    club_player.is_featured = True
                    changed_fields.append("is_featured")

                if club_player.display_order == 0 and stat.display_order:
                    club_player.display_order = stat.display_order
                    changed_fields.append("display_order")

                if changed_fields:
                    club_player.save(update_fields=changed_fields)

            stat.club_player = club_player
            stat.save(update_fields=["club_player"])

            linked_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Hotovo. "
                f"Vytvorených ClubPlayer: {created_count}, "
                f"prepojených statov: {linked_count}, "
                f"preskočených: {skipped_count}"
            )
        )