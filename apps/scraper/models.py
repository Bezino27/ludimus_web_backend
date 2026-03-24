from django.db import models


class SzfbCompetition(models.Model):
    szfb_competition_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    season = models.CharField(max_length=50, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    standings_url = models.URLField(blank=True, default="")
    results_url = models.URLField(blank=True, default="")
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.season})"


class SzfbStandingRow(models.Model):
    competition = models.ForeignKey(
        SzfbCompetition,
        on_delete=models.CASCADE,
        related_name="standings",
    )
    position = models.PositiveIntegerField()
    team_name = models.CharField(max_length=255)
    played = models.PositiveIntegerField(default=0)
    points = models.IntegerField(default=0)

    class Meta:
        ordering = ["position"]
        unique_together = ("competition", "position")

    def __str__(self):
        return f"{self.position}. {self.team_name} - {self.points}b"


class SzfbTeamWatch(models.Model):
    label = models.CharField(max_length=255)
    competition = models.ForeignKey(
        SzfbCompetition,
        on_delete=models.CASCADE,
        related_name="watched_teams",
    )
    team_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class SzfbMatch(models.Model):
    MATCH_TYPE_CHOICES = [
        ("finished", "Finished"),
        ("upcoming", "Upcoming"),
    ]

    watched_team = models.ForeignKey(
        SzfbTeamWatch,
        on_delete=models.CASCADE,
        related_name="matches",
    )

    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES)
    match_date = models.DateField(null=True, blank=True)
    match_time = models.TimeField(null=True, blank=True)

    opponent = models.CharField(max_length=255)
    venue = models.CharField(max_length=255, blank=True, default="")
    result = models.CharField(max_length=30, blank=True, default="")
    is_home = models.BooleanField(null=True, blank=True)

    external_key = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["match_date", "match_time"]

    def __str__(self):
        return f"{self.watched_team.label} vs {self.opponent} ({self.match_type})"