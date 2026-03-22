from django.db import models
from apps.common.models import TimeStampedModel


class Team(TimeStampedModel):
    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=150)
    slug = models.SlugField()
    season = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("club", "slug")
        ordering = ["name"]

    def __str__(self):
        return f"{self.club.name} - {self.name}"


class TeamMember(TimeStampedModel):
    ROLE_CHOICES = [
        ("player", "Player"),
        ("coach", "Coach"),
        ("staff", "Staff"),
    ]

    club = models.ForeignKey("clubs.Club", on_delete=models.CASCADE, related_name="team_members")
    team = models.ForeignKey("teams.Team", on_delete=models.SET_NULL, null=True, blank=True, related_name="members")

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    position = models.CharField(max_length=100, blank=True)
    jersey_number = models.PositiveIntegerField(null=True, blank=True)
    photo = models.ImageField(upload_to="teams/members/", blank=True, null=True)

    bio = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"