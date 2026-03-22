from django.db import models
from apps.common.models import TimeStampedModel


class Document(TimeStampedModel):
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/")
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title