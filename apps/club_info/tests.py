from django.test import TestCase

from apps.club_info.revalidation import get_club_link_revalidation_paths
from apps.clubs.models import Club
from apps.teams.models import Category


class ClubLinkRevalidationTests(TestCase):
    def test_only_server_side_category_consumers_are_returned(self):
        club = Club.objects.create(name="ATU", slug="atu")
        Category.objects.create(
            club=club, name="Muži", slug="muzi", season="2026/2027",
            birth_year_from=1990, birth_year_to=2010,
        )
        self.assertEqual(get_club_link_revalidation_paths(club), ["/kategorie/muzi"])
