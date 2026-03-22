from django.db import models
from apps.common.models import TimeStampedModel


class Partner(TimeStampedModel):
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="partners")
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="partners/", blank=True, null=True)
    website = models.URLField(blank=True)
    tier = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name