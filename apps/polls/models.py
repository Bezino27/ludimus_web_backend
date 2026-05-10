from itertools import combinations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Poll(models.Model):
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
            for poll in Poll.objects.filter(is_active=True).exclude(pk=self.pk)
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
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name="options",
    )
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.poll.question} - {self.text}"


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