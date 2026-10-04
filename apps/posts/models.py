import logging

from django.conf import settings
from django.db import models
from PIL import Image

from apps.common.models import TimeStampedModel


logger = logging.getLogger(__name__)


class PostCategory(TimeStampedModel):
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="post_categories")
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    class Meta:
        unique_together = ("club", "slug")
        ordering = ["name"]

    def __str__(self):
        return f"{self.club.name} - {self.name}"


class Post(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("scheduled", "Scheduled"),
        ("archived", "Archived"),
    ]

    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="posts")
    category = models.ForeignKey(
        "posts.PostCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts"
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField()
    excerpt = models.TextField(blank=True)
    content = models.TextField()

    featured_image = models.ImageField(upload_to="posts/featured/", blank=True, null=True)
    image_width = models.PositiveIntegerField(blank=True, null=True, editable=False)
    image_height = models.PositiveIntegerField(blank=True, null=True, editable=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(blank=True, null=True)

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    is_featured = models.BooleanField(default=False)

    external_source = models.CharField(max_length=100, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    source_url = models.URLField(blank=True)

    class Meta:
        unique_together = ("club", "slug")
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def read_featured_image_dimensions(self):
        if not self.featured_image:
            return None, None

        is_committed = self.featured_image._committed

        if is_committed:
            self.featured_image.open("rb")

        image_file = self.featured_image.file

        try:
            image_file.seek(0)
        except (AttributeError, OSError):
            pass

        try:
            with Image.open(image_file) as image:
                width, height = image.size
        finally:
            if is_committed:
                self.featured_image.close()
            else:
                try:
                    image_file.seek(0)
                except (AttributeError, OSError):
                    pass

        if width <= 0 or height <= 0:
            raise ValueError("Image dimensions must be positive.")

        return width, height

    def save(self, *args, **kwargs):
        image_name = getattr(self.featured_image, "name", "") or ""
        previous_image_name = None

        if self.pk:
            previous_image_name = (
                type(self).objects.filter(pk=self.pk)
                .values_list("featured_image", flat=True)
                .first()
            )

        image_changed = self._state.adding or previous_image_name != image_name
        dimensions_missing = bool(image_name) and (
            self.image_width is None or self.image_height is None
        )
        dimensions_changed = image_changed or dimensions_missing

        if dimensions_changed:
            if image_name:
                try:
                    self.image_width, self.image_height = (
                        self.read_featured_image_dimensions()
                    )
                except Exception:
                    logger.warning(
                        "Could not read featured image dimensions for post %s (%s).",
                        self.pk or "new",
                        image_name,
                        exc_info=True,
                    )
                    self.image_width = None
                    self.image_height = None
            else:
                self.image_width = None
                self.image_height = None

            update_fields = kwargs.get("update_fields")

            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {
                    "image_width",
                    "image_height",
                }

        return super().save(*args, **kwargs)
