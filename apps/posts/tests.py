from django.test import TestCase

from apps.clubs.models import Club
from apps.posts.models import Post, PostCategory
from apps.posts.revalidation import get_post_category_revalidation_paths, get_post_revalidation_paths
from apps.teams.models import Category


class PostRevalidationTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU", slug="atu")
        Category.objects.create(
            club=self.club, name="Muži", slug="muzi", season="2026/2027",
            birth_year_from=1990, birth_year_to=2010,
        )
        self.post_category = PostCategory.objects.create(
            club=self.club, name="Novinky", slug="novinky"
        )
        self.post = Post.objects.create(
            club=self.club, category=self.post_category, title="Článok",
            slug="clanok", content="Text", status="published",
        )

    def test_post_includes_shared_category_feed_and_old_slug(self):
        self.assertEqual(
            get_post_revalidation_paths(self.post, old_slug="stary"),
            ["/", "/clanky", "/sitemap.xml", "/clanky/clanok", "/clanky/stary", "/kategorie/muzi"],
        )

    def test_post_category_includes_details_and_team_categories(self):
        self.assertEqual(
            get_post_category_revalidation_paths(self.post_category),
            ["/", "/clanky", "/sitemap.xml", "/kategorie/muzi", "/clanky/clanok"],
        )
