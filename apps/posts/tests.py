from datetime import datetime
from io import BytesIO, StringIO
import shutil
import tempfile
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from apps.clubs.models import Club
from apps.posts.models import Post, PostCategory
from apps.posts.revalidation import get_post_category_revalidation_paths, get_post_revalidation_paths
from apps.teams.models import Category


def create_test_image(name="test.png", size=(640, 360), color=(20, 30, 40)):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")

    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="image/png",
    )


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


class PostImageMetadataTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def create_post(self, **kwargs):
        defaults = {
            "club": self.club,
            "title": "Obrázkový článok",
            "slug": "obrazkovy-clanok",
            "content": "Text článku",
            "status": "published",
        }
        defaults.update(kwargs)
        return Post.objects.create(**defaults)

    def test_post_without_image_has_null_dimensions(self):
        post = self.create_post()

        self.assertIsNone(post.image_width)
        self.assertIsNone(post.image_height)

        response = self.client.get(
            f"/api/public/posts/{self.club.slug}/{post.slug}/",
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["image_width"])
        self.assertIsNone(response.json()["image_height"])

    def test_new_and_replaced_image_refresh_dimensions(self):
        post = self.create_post(
            featured_image=create_test_image(size=(640, 360)),
        )

        self.assertEqual((post.image_width, post.image_height), (640, 360))

        post.featured_image = create_test_image(
            name="replacement.png",
            size=(320, 480),
        )
        post.save(update_fields=["featured_image"])
        post.refresh_from_db()

        self.assertEqual((post.image_width, post.image_height), (320, 480))

    def test_public_api_exposes_image_dimensions(self):
        post = self.create_post(
            featured_image=create_test_image(size=(800, 600)),
        )

        response = self.client.get(
            f"/api/public/posts/{self.club.slug}/{post.slug}/",
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["image_width"], 800)
        self.assertEqual(response.json()["image_height"], 600)

    def test_backfill_updates_existing_image_without_reupload(self):
        post = self.create_post(
            featured_image=create_test_image(size=(1024, 576)),
        )
        original_name = post.featured_image.name
        Post.objects.filter(pk=post.pk).update(
            image_width=None,
            image_height=None,
        )
        stdout = StringIO()

        call_command("backfill_post_image_dimensions", stdout=stdout)
        post.refresh_from_db()

        self.assertEqual(post.featured_image.name, original_name)
        self.assertEqual((post.image_width, post.image_height), (1024, 576))
        self.assertIn("updated=1", stdout.getvalue())

    def test_backfill_dry_run_does_not_write_dimensions(self):
        post = self.create_post(
            featured_image=create_test_image(size=(500, 250)),
        )
        Post.objects.filter(pk=post.pk).update(
            image_width=None,
            image_height=None,
        )
        stdout = StringIO()

        call_command(
            "backfill_post_image_dimensions",
            "--dry-run",
            stdout=stdout,
        )
        post.refresh_from_db()

        self.assertIsNone(post.image_width)
        self.assertIsNone(post.image_height)
        self.assertIn("would update=1", stdout.getvalue())

    def test_backfill_keeps_existing_dimensions(self):
        post = self.create_post(
            featured_image=create_test_image(size=(500, 250)),
        )
        Post.objects.filter(pk=post.pk).update(
            image_width=111,
            image_height=222,
        )
        stdout = StringIO()

        call_command("backfill_post_image_dimensions", stdout=stdout)
        post.refresh_from_db()

        self.assertEqual((post.image_width, post.image_height), (111, 222))
        self.assertIn("already_populated=1", stdout.getvalue())

    def test_missing_file_is_reported_without_stopping_backfill(self):
        post = self.create_post()
        Post.objects.filter(pk=post.pk).update(
            featured_image="posts/featured/missing.png",
            image_width=None,
            image_height=None,
        )
        stdout = StringIO()
        stderr = StringIO()

        call_command(
            "backfill_post_image_dimensions",
            stdout=stdout,
            stderr=stderr,
        )

        self.assertIn("failed=1", stdout.getvalue())
        self.assertIn(f"Post {post.pk}", stderr.getvalue())

    def test_corrupt_file_is_reported_without_stopping_backfill(self):
        corrupt_path = default_storage.save(
            "posts/featured/corrupt.png",
            ContentFile(b"not-an-image"),
        )
        post = self.create_post()
        Post.objects.filter(pk=post.pk).update(
            featured_image=corrupt_path,
            image_width=None,
            image_height=None,
        )
        stdout = StringIO()
        stderr = StringIO()

        call_command(
            "backfill_post_image_dimensions",
            stdout=stdout,
            stderr=stderr,
        )

        self.assertIn("failed=1", stdout.getvalue())
        self.assertIn("UnidentifiedImageError", stderr.getvalue())
