from django.db import models
from apps.common.models import TimeStampedModel


class GalleryAlbum(TimeStampedModel):
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="gallery_albums")
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="gallery/covers/", blank=True, null=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        unique_together = ("club", "slug")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class GalleryImage(TimeStampedModel):
    album = models.ForeignKey("gallery.GalleryAlbum", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="gallery/images/")
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Image {self.id} - {self.album.title}"