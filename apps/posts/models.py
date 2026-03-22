from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedModel


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