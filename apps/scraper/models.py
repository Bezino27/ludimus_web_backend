from datetime import datetime, time as datetime_time, timedelta
import re
import unicodedata

from django.db import models
from django.utils import timezone


def normalize_player_name(value: str) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def build_club_player_identity_key(full_name: str, birth_year) -> str:
    normalized_name = normalize_player_name(full_name)
    normalized_birth_year = birth_year or ""
    return f"{normalized_name}|{normalized_birth_year}"


def default_auto_sync_time():
    return datetime_time(hour=6, minute=0)


class SzfbCompetition(models.Model):
    SYNC_STATUS_IDLE = "idle"
    SYNC_STATUS_RUNNING = "running"
    SYNC_STATUS_SUCCESS = "success"
    SYNC_STATUS_ERROR = "error"

    SYNC_STATUS_CHOICES = [
        (SYNC_STATUS_IDLE, "Neaktívne"),
        (SYNC_STATUS_RUNNING, "Prebieha"),
        (SYNC_STATUS_SUCCESS, "Hotovo"),
        (SYNC_STATUS_ERROR, "Chyba"),
    ]

    szfb_competition_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    season = models.CharField(max_length=50, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    standings_url = models.URLField(blank=True, default="")
    results_url = models.URLField(blank=True, default="")
    last_synced_at = models.DateTimeField(null=True, blank=True)

    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default=SYNC_STATUS_IDLE,
    )
    sync_started_at = models.DateTimeField(null=True, blank=True)
    sync_finished_at = models.DateTimeField(null=True, blank=True)
    sync_last_attempt_at = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True, default="")

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
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="szfb_team_watches",
        null=True,
        blank=True,
    )
    team_name = models.CharField(max_length=255)
    competitor_id = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class ClubPlayer(models.Model):
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="club_players",
    )

    full_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, db_index=True)
    identity_key = models.CharField(max_length=320, db_index=True)

    birth_year = models.PositiveIntegerField(null=True, blank=True)

    height_cm = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.PositiveIntegerField(null=True, blank=True)

    photo = models.ImageField(upload_to="players/photos/", null=True, blank=True)
    jersey_number = models.PositiveIntegerField(null=True, blank=True)
    position = models.CharField(max_length=50, blank=True, default="")
    bio = models.TextField(blank=True, default="")

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "identity_key"],
                name="unique_club_player_identity",
            )
        ]

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_player_name(self.full_name)
        self.identity_key = build_club_player_identity_key(
            self.full_name,
            self.birth_year,
        )
        super().save(*args, **kwargs)

    def __str__(self):
        if self.birth_year:
            return f"{self.full_name} ({self.birth_year})"

        return self.full_name


class SzfbAutoSyncConfig(models.Model):
    FREQUENCY_DAILY = "daily"
    FREQUENCY_WEEKLY = "weekly"

    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, "Každý deň"),
        (FREQUENCY_WEEKLY, "Každý týždeň"),
    ]

    WEEKDAY_MONDAY = 0
    WEEKDAY_TUESDAY = 1
    WEEKDAY_WEDNESDAY = 2
    WEEKDAY_THURSDAY = 3
    WEEKDAY_FRIDAY = 4
    WEEKDAY_SATURDAY = 5
    WEEKDAY_SUNDAY = 6

    WEEKDAY_CHOICES = [
        (WEEKDAY_MONDAY, "Pondelok"),
        (WEEKDAY_TUESDAY, "Utorok"),
        (WEEKDAY_WEDNESDAY, "Streda"),
        (WEEKDAY_THURSDAY, "Štvrtok"),
        (WEEKDAY_FRIDAY, "Piatok"),
        (WEEKDAY_SATURDAY, "Sobota"),
        (WEEKDAY_SUNDAY, "Nedeľa"),
    ]

    STATUS_IDLE = "idle"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_IDLE, "Neaktívne"),
        (STATUS_SUCCESS, "Hotovo"),
        (STATUS_ERROR, "Chyba"),
        (STATUS_SKIPPED, "Preskočené"),
    ]

    club = models.OneToOneField(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="szfb_auto_sync_config",
    )

    is_enabled = models.BooleanField(default=False)
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default=FREQUENCY_WEEKLY,
    )
    weekday = models.PositiveSmallIntegerField(
        choices=WEEKDAY_CHOICES,
        default=WEEKDAY_MONDAY,
    )
    run_time = models.TimeField(default=default_auto_sync_time)

    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    last_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IDLE,
    )
    last_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SZFB automatická synchronizácia"
        verbose_name_plural = "SZFB automatické synchronizácie"

    def __str__(self):
        return f"{self.club} - SZFB auto sync"

    def calculate_next_run_at(self, from_datetime=None):
        current = timezone.localtime(from_datetime or timezone.now())
        current_timezone = timezone.get_current_timezone()
        run_time = self.run_time or default_auto_sync_time()

        if isinstance(run_time, str):
            hour, minute = run_time.split(":")[:2]
            run_time = datetime_time(hour=int(hour), minute=int(minute))
        if self.frequency == self.FREQUENCY_DAILY:
            candidate_date = current.date()
            candidate = timezone.make_aware(
                datetime.combine(candidate_date, run_time),
                current_timezone,
            )

            if candidate <= current:
                candidate += timedelta(days=1)

            return candidate

        days_ahead = (self.weekday - current.weekday()) % 7
        candidate_date = current.date() + timedelta(days=days_ahead)
        candidate = timezone.make_aware(
            datetime.combine(candidate_date, run_time),
            current_timezone,
        )

        if candidate <= current:
            candidate += timedelta(days=7)

        return candidate

    def refresh_next_run_at(self, from_datetime=None, save=True):
        self.next_run_at = self.calculate_next_run_at(from_datetime)

        if save:
            self.save(update_fields=["next_run_at", "updated_at"])

        return self.next_run_at

    def is_due(self, now=None):
        if not self.is_enabled:
            return False

        current = now or timezone.now()

        if not self.next_run_at:
            return False

        return self.next_run_at <= current


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


class SzfbPlayerStat(models.Model):
    watched_team = models.ForeignKey(
        SzfbTeamWatch,
        on_delete=models.CASCADE,
        related_name="player_stats",
    )
    club_player = models.ForeignKey(
        ClubPlayer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="szfb_stats",
    )

    rank = models.PositiveIntegerField()
    player_name = models.CharField(max_length=255)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    team_short_name = models.CharField(max_length=50, blank=True, default="")
    player_position = models.CharField(max_length=20, blank=True, default="")

    games = models.PositiveIntegerField(default=0)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=0)

    points_avg = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # # DOČASNÉ STARÉ KLUBOVÉ ÚDAJE
    # Zatiaľ ich nemažeme. Použijeme ich na migráciu do ClubPlayer.
    photo = models.ImageField(upload_to="players/photos/", null=True, blank=True)
    jersey_number = models.PositiveIntegerField(null=True, blank=True)
    bio = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    esp = models.PositiveIntegerField(default=0)
    ppp = models.PositiveIntegerField(default=0)
    shp = models.PositiveIntegerField(default=0)
    pim = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["rank"]
        unique_together = ("watched_team", "rank", "player_name")

    def __str__(self):
        return f"{self.rank}. {self.player_name} - {self.points}b"