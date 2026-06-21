from django.conf import settings
from django.db import models
from apps.common.models import TimeStampedModel


class Club(TimeStampedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    short_name = models.CharField(max_length=100, blank=True)

    description = models.TextField(blank=True)

    logo = models.ImageField(upload_to="clubs/logos/", blank=True, null=True)
    cover_image = models.ImageField(upload_to="clubs/covers/", blank=True, null=True)

    primary_color = models.CharField(max_length=20, default="#000000")
    secondary_color = models.CharField(max_length=20, default="#ffffff")
    accent_color = models.CharField(max_length=20, default="#D32F2F")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ClubMembership(TimeStampedModel):
    ROLE_CHOICES = [
        ("club_admin", "Club admin"),
        ("editor", "Editor"),
        ("match_manager", "Match manager"),
        ("viewer", "Viewer"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="club_memberships")
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "club", "role")
        ordering = ["club__name", "user__username", "role"]

    def __str__(self):
        return f"{self.user} - {self.club} - {self.role}"
    
