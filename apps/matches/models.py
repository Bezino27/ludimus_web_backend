from django.db import models
from apps.common.models import TimeStampedModel


class Match(TimeStampedModel):
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="matches")
    category = models.ForeignKey(
        "teams.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches"
    )
    opponent = models.CharField(max_length=255)
    competition = models.CharField(max_length=255, blank=True)
    round_label = models.CharField(max_length=100, blank=True)

    match_date = models.DateTimeField()
    location = models.CharField(max_length=255, blank=True)
    is_home = models.BooleanField(default=True)

    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)

    summary = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    external_source = models.CharField(max_length=100, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-match_date"]

    def __str__(self):
        return f"{self.club.name} vs {self.opponent}"