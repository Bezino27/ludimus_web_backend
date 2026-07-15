from itertools import combinations
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import URLValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone


class Poll(models.Model):
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="polls",
        null=True,
        blank=True,
    )
    question = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    # Ručný hlavný vypínač.
    # Ak je False, anketa sa vypne okamžite, aj keď je práve v správnom čase.
    # Ak je True, anketa môže bežať podľa starts_at a ends_at.
    is_active = models.BooleanField(default=False)

    # Časové okno ankety.
    # Anketu vieš pripraviť dopredu a sama sa otvorí v čase starts_at.
    # Po ends_at sa automaticky prestane dať hlasovať.
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError("Koniec ankety musí byť neskôr ako začiatok ankety.")

        if not self.is_active:
            return

        overlapping_polls = [
            poll
            for poll in Poll.objects.filter(
                is_active=True,
                club=self.club,
            ).exclude(pk=self.pk)
            if self._intervals_overlap(
                self.starts_at,
                self.ends_at,
                poll.starts_at,
                poll.ends_at,
            )
        ]

        for poll_a, poll_b in combinations(overlapping_polls, 2):
            if self._three_intervals_overlap(
                self.starts_at,
                self.ends_at,
                poll_a.starts_at,
                poll_a.ends_at,
                poll_b.starts_at,
                poll_b.ends_at,
            ):
                raise ValidationError(
                    "V tomto časovom intervale by boli aktívne viac ako 2 ankety naraz."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @staticmethod
    def _intervals_overlap(start_a, end_a, start_b, end_b):
        """
        Kontroluje, či sa dva časové intervaly prekrývajú.

        None pri starts_at znamená: anketa nemá presný začiatok.
        None pri ends_at znamená: anketa nemá presný koniec.
        """
        starts_before_other_ends = end_b is None or start_a is None or start_a < end_b
        ends_after_other_starts = end_a is None or start_b is None or end_a > start_b

        return starts_before_other_ends and ends_after_other_starts

    @staticmethod
    def _three_intervals_overlap(
        start_a,
        end_a,
        start_b,
        end_b,
        start_c,
        end_c,
    ):
        """
        Kontroluje, či existuje časový moment,
        v ktorom sa prekrývajú všetky 3 ankety naraz.

        Toto je dôležité pre pravidlo:
        maximálne 2 ankety môžu bežať v rovnakom čase.
        """
        starts = [value for value in [start_a, start_b, start_c] if value is not None]
        ends = [value for value in [end_a, end_b, end_c] if value is not None]

        latest_start = max(starts) if starts else None
        earliest_end = min(ends) if ends else None

        if latest_start is None or earliest_end is None:
            return True

        return latest_start < earliest_end

    @property
    def is_open_for_voting(self):
        """
        Toto je reálny stav ankety.

        is_active = admin ju povolil
        starts_at = už začala?
        ends_at = ešte neskončila?

        Ak toto vráti True, používateľ môže hlasovať.
        """
        now = timezone.now()

        if not self.is_active:
            return False

        if self.starts_at and now < self.starts_at:
            return False

        if self.ends_at and now > self.ends_at:
            return False

        return True

    def __str__(self):
        return self.question


class PollOption(models.Model):
    ALLOWED_VIDEO_FILE_EXTENSIONS = {".mp4", ".webm", ".mov"}
    ALLOWED_VIDEO_FILE_MIME_TYPES = {"video/mp4", "video/webm", "video/quicktime"}

    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="options",
    )
    text = models.CharField(max_length=255)
    video_url = models.URLField(blank=True, default="")
    video_file = models.FileField(upload_to="polls/videos/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.poll.question} - {self.text}"

    def clean(self):
        super().clean()

        if self.video_file:
            self._validate_video_file()

        if not self.video_url:
            return

        URLValidator(schemes=["http", "https"])(self.video_url)
        parsed_url = urlparse(self.video_url)
        hostname = (parsed_url.hostname or "").lower()
        path = parsed_url.path.lower()

        is_youtube = (
            hostname == "youtu.be" and bool(path.strip("/"))
        ) or (
            hostname in {"youtube.com", "www.youtube.com"}
            and path == "/watch"
            and bool(parsed_url.query)
            and "v=" in parsed_url.query
        )
        is_vimeo = (
            hostname in {"vimeo.com", "www.vimeo.com"}
            and path.strip("/").isdigit()
        ) or (
            hostname == "player.vimeo.com"
            and path.startswith("/video/")
            and path.removeprefix("/video/").strip("/").isdigit()
        )
        is_mp4 = path.endswith(".mp4")

        if not (is_youtube or is_vimeo or is_mp4):
            raise ValidationError({
                "video_url": "Podporované sú iba YouTube, Vimeo alebo priame MP4 URL."
            })

    def save(self, *args, **kwargs):
        self.video_url = (self.video_url or "").strip()
        old_video_file_name = self._get_old_video_file_name()

        self.full_clean()
        super().save(*args, **kwargs)

        if (
            old_video_file_name
            and old_video_file_name != (self.video_file.name if self.video_file else "")
        ):
            default_storage.delete(old_video_file_name)

    def _get_old_video_file_name(self):
        if not self.pk:
            return ""

        return (
            PollOption.objects.filter(pk=self.pk)
            .values_list("video_file", flat=True)
            .first()
            or ""
        )

    def _validate_video_file(self):
        file_extension = Path(self.video_file.name).suffix.lower()

        if file_extension not in self.ALLOWED_VIDEO_FILE_EXTENSIONS:
            raise ValidationError({
                "video_file": "Video súbor musí byť vo formáte MP4, WebM alebo MOV."
            })

        content_type = getattr(self.video_file.file, "content_type", "")

        if content_type and content_type not in self.ALLOWED_VIDEO_FILE_MIME_TYPES:
            raise ValidationError({
                "video_file": "Nepodporovaný MIME typ video súboru."
            })

        max_size = getattr(settings, "POLL_OPTION_VIDEO_MAX_UPLOAD_SIZE", 100 * 1024 * 1024)
        file_size = getattr(self.video_file, "size", 0)

        if file_size and file_size > max_size:
            raise ValidationError({
                "video_file": "Video súbor môže mať najviac 100 MB."
            })


@receiver(post_delete, sender=PollOption)
def delete_poll_option_video_file(sender, instance, **kwargs):
    if instance.video_file:
        default_storage.delete(instance.video_file.name)


class PollVote(models.Model):
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    option = models.ForeignKey(
        PollOption,
        on_delete=models.CASCADE,
        related_name="votes",
    )

    # Anonymné ID zariadenia / prehliadača.
    # Podľa toho budeme kontrolovať, aby rovnaké zariadenie nehlasovalo viackrát.
    voter_id = models.CharField(max_length=100)

    # IP a user-agent budeme ukladať zahashované.
    # Nie ako čistý text.
    ip_hash = models.CharField(max_length=128, blank=True, default="")
    user_agent_hash = models.CharField(max_length=128, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "voter_id"],
                name="unique_vote_per_poll_per_voter",
            )
        ]

    def clean(self):
        if self.option and self.poll and self.option.poll_id != self.poll_id:
            raise ValidationError("Táto možnosť nepatrí k tejto ankete.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hlas: {self.poll.question} -> {self.option.text}"
