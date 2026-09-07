from django.test import TestCase

from apps.clubs.models import Club
from apps.teams.models import Category, CategoryLink, CategoryTraining, ClubSeason, TrainingLocation
from apps.teams.revalidation import (
    get_category_child_revalidation_paths,
    get_category_revalidation_paths,
    get_club_season_revalidation_paths,
    get_training_location_revalidation_paths,
)


class TeamRevalidationTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU", slug="atu")
        self.category = Category.objects.create(
            club=self.club, name="Muži", slug="muzi", season="2026/2027",
            birth_year_from=1990, birth_year_to=2010,
        )

    def test_category_paths_cover_detail_recruitment_home_and_old_slug(self):
        self.assertEqual(
            get_category_revalidation_paths(self.category, old_slug="seniori"),
            ["/kategorie/muzi", "/pridaj_sa", "/kategorie/seniori", "/"],
        )

    def test_category_training_uses_category_detail(self):
        self.assertEqual(get_category_child_revalidation_paths(self.category), ["/kategorie/muzi"])

    def test_category_link_uses_category_detail(self):
        CategoryLink.objects.create(category=self.category, title="Web", url="https://example.com")
        self.assertEqual(get_category_child_revalidation_paths(self.category), ["/kategorie/muzi"])

    def test_training_location_returns_linked_categories(self):
        location = TrainingLocation.objects.create(
            club=self.club, name="Hala", latitude=48.7, longitude=21.2
        )
        CategoryTraining.objects.create(
            category=self.category, location=location, weekday=1, start_time="18:00"
        )
        self.assertEqual(get_training_location_revalidation_paths(location), ["/kategorie/muzi"])

    def test_club_season_covers_home_recruitment_and_categories(self):
        season = ClubSeason.objects.create(club=self.club, season="2026/2027")
        self.assertEqual(
            get_club_season_revalidation_paths(season),
            ["/", "/pridaj_sa", "/kategorie/muzi"],
        )
