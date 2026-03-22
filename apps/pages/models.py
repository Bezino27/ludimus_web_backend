from django.db import models
from apps.common.models import TimeStampedModel


class Page(TimeStampedModel):
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="pages")
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    content = models.TextField(blank=True)

    is_published = models.BooleanField(default=True)
    show_in_menu = models.BooleanField(default=False)
    menu_order = models.PositiveIntegerField(default=0)

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    class Meta:
        unique_together = ("club", "slug")
        ordering = ["menu_order", "title"]

    def __str__(self):
        return f"{self.club.name} - {self.title}"