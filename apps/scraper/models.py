from django.db import models
from apps.common.models import TimeStampedModel


class ScraperSource(TimeStampedModel):
    SOURCE_TYPE_CHOICES = [
        ("posts", "Posts"),
        ("matches", "Matches"),
        ("table", "Table"),
        ("gallery", "Gallery"),
    ]

    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="scraper_sources")
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPE_CHOICES)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["club__name", "name"]

    def __str__(self):
        return f"{self.club.name} - {self.name}"


class ScraperJob(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    source = models.ForeignKey("scraper.ScraperSource", on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    log = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source.name} - {self.status}"