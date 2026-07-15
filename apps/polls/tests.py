import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clubs.models import Club

from apps.polls.models import Poll, PollOption, PollVote
from apps.polls.serializers import PollSerializer


class PollVideoUrlTests(TestCase):
    def setUp(self):
        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.poll = Poll.objects.create(
            club=self.club,
            question="Najlepší hráč?",
            is_active=True,
            starts_at=timezone.now(),
        )

    def create_option(self, video_url=""):
        return PollOption.objects.create(
            poll=self.poll,
            text="Možnosť",
            video_url=video_url,
            order=0,
        )

    def test_create_option_without_video_url(self):
        option = self.create_option()

        self.assertEqual(option.video_url, "")

    def test_create_option_with_youtube_url(self):
        option = self.create_option("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        self.assertEqual(option.video_url, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_create_option_with_vimeo_url(self):
        option = self.create_option("https://vimeo.com/123456789")

        self.assertEqual(option.video_url, "https://vimeo.com/123456789")

    def test_create_option_with_mp4_url(self):
        option = self.create_option("https://example.com/video.mp4")

        self.assertEqual(option.video_url, "https://example.com/video.mp4")

    def test_invalid_video_url_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.create_option("https://example.com/video.mov")

    def test_public_serializer_returns_video_url(self):
        self.create_option("https://youtu.be/dQw4w9WgXcQ")

        data = PollSerializer(self.poll).data

        self.assertEqual(data["options"][0]["video_url"], "https://youtu.be/dQw4w9WgXcQ")

    def test_existing_voting_still_works(self):
        option = self.create_option("https://example.com/video.mp4")
        client = APIClient()
        response = client.post(
            reverse("poll-vote", kwargs={"poll_id": self.poll.id}),
            {"option_id": option.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(PollVote.objects.filter(poll=self.poll, option=option).exists())


class PollOptionVideoFileTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(
            MEDIA_ROOT=self.media_root,
            POLL_OPTION_VIDEO_MAX_UPLOAD_SIZE=1024,
        )
        self.override.enable()

        self.club = Club.objects.create(name="ATU Košice", slug="atu-kosice")
        self.poll = Poll.objects.create(
            club=self.club,
            question="Najlepšie video?",
            is_active=True,
            starts_at=timezone.now(),
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def create_video_file(self, name="video.mp4", content=b"video", content_type="video/mp4"):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_create_option_with_video_file(self):
        option = PollOption.objects.create(
            poll=self.poll,
            text="Súbor",
            video_file=self.create_video_file(),
            order=0,
        )

        self.assertTrue(option.video_file.name.startswith("polls/videos/"))

    def test_invalid_video_file_extension_is_rejected(self):
        with self.assertRaises(ValidationError):
            PollOption.objects.create(
                poll=self.poll,
                text="Zlý súbor",
                video_file=self.create_video_file("video.avi", content_type="video/avi"),
                order=0,
            )

    def test_too_large_video_file_is_rejected(self):
        with self.assertRaises(ValidationError):
            PollOption.objects.create(
                poll=self.poll,
                text="Veľký súbor",
                video_file=self.create_video_file(content=b"x" * 2048),
                order=0,
            )

    def test_public_serializer_returns_absolute_video_file_url(self):
        option = PollOption.objects.create(
            poll=self.poll,
            text="Súbor",
            video_file=self.create_video_file(),
            order=0,
        )

        request = APIClient().get("/").wsgi_request
        data = PollSerializer(self.poll, context={"request": request}).data

        self.assertEqual(data["options"][0]["id"], option.id)
        self.assertTrue(data["options"][0]["video_file_url"].startswith("http://testserver/media/"))
