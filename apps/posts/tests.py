from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
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


class PublicPostDetailTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.author = get_user_model().objects.create_user(
            username="guli",
            first_name="Martin",
            last_name="Gulaš",
            password="test-password",
        )

    def test_detail_response_contains_published_at(self):
        published_at = datetime(
            2026,
            9,
            10,
            18,
            30,
            tzinfo=ZoneInfo("Europe/Bratislava"),
        )
        post = Post.objects.create(
            club=self.club,
            author=self.author,
            title="Testovací článok",
            slug="testovaci-clanok",
            content="Text článku",
            status="published",
            published_at=published_at,
        )

        response = self.client.get(
            f"/api/public/posts/{self.club.slug}/{post.slug}/",
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], post.slug)
        self.assertEqual(response.json()["title"], post.title)
        self.assertEqual(response.json()["author_first_name"], "Martin")
        self.assertEqual(response.json()["author_last_name"], "Gulaš")
        self.assertEqual(response.json()["author_name"], "Gulaš Martin")
        self.assertEqual(
            response.json()["published_at"],
            "2026-09-10T18:30:00+02:00",
        )

    def test_detail_uses_created_at_for_legacy_post_without_published_at(self):
        post = Post.objects.create(
            club=self.club,
            author=self.author,
            title="Starší článok",
            slug="starsi-clanok",
            content="Text článku",
            status="published",
        )

        response = self.client.get(
            f"/api/public/posts/{self.club.slug}/{post.slug}/",
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["published_at"])
