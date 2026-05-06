from django.db import models
from apps.common.models import TimeStampedModel


class HomepageSection(TimeStampedModel):
    SECTION_TYPES = [
        ("hero", "Hero"),
        ("latest_posts", "Latest posts"),
        ("partners", "Partners"),
        ("gallery", "Gallery"),
        ("cta", "CTA"),
        ("custom_html", "Custom HTML"),
    ]

    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="homepage_sections")
    title = models.CharField(max_length=255, blank=True)
    section_type = models.CharField(max_length=50, choices=SECTION_TYPES)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.club.name} - {self.section_type}"
