from django.db import models
from apps.common.models import TimeStampedModel


class Category(TimeStampedModel):
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField()
    season = models.CharField(max_length=20)
    birth_year_from = models.PositiveIntegerField()
    birth_year_to = models.PositiveIntegerField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    category_subname = models.CharField(
        max_length=30,
        blank=True,
        help_text="Krátky vizuálny názov kategórie, napr. MEX, U19, U17, U11-U9.",
    )

    coach_name = models.CharField(max_length=150, blank=True)
    coach_email = models.EmailField(blank=True)
    coach_phone = models.CharField(max_length=30, blank=True)

    league_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Názov ligy zobrazovaný na webe, napr. Slovenská florbalová extraliga.",
    )

    hero_image = models.ImageField(
        upload_to="categories/hero/",
        blank=True,
        null=True,
        help_text="Hlavná fotka kategórie zobrazovaná v hero sekcii na webe.",
    )
    szfb_team_watch = models.ForeignKey(
        "scraper.SzfbTeamWatch",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_categories",
        help_text="SZFB sledovanie, z ktorého web číta tabuľku, zápasy a štatistiky.",
    )

    class Meta:
        unique_together = ("club", "slug", "season")
        ordering = ["order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.club.name} - {self.name} ({self.season})"


class TrainingLocation(TimeStampedModel):
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="training_locations",
    )
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["club", "name"],
                name="unique_training_location_name_per_club",
            )
        ]
        verbose_name = "Training location"
        verbose_name_plural = "Training locations"

    def __str__(self):
        return f"{self.club.name} - {self.name}"


class CategoryTraining(TimeStampedModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 1, "Pondelok"
        TUESDAY = 2, "Utorok"
        WEDNESDAY = 3, "Streda"
        THURSDAY = 4, "Štvrtok"
        FRIDAY = 5, "Piatok"
        SATURDAY = 6, "Sobota"
        SUNDAY = 7, "Nedeľa"

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="trainings",
    )
    location = models.ForeignKey(
        TrainingLocation,
        on_delete=models.PROTECT,
        related_name="category_trainings",
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "weekday", "start_time", "location"],
                name="unique_category_training_slot",
            )
        ]
        verbose_name = "Category training"
        verbose_name_plural = "Category trainings"

    def __str__(self):
        return (
            f"{self.category.name} - {self.get_weekday_display()} "
            f"{self.start_time.strftime('%H:%M')}"
        )


class CategoryLink(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="links",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    cta_text = models.CharField(max_length=100, blank=True)
    url = models.URLField(max_length=500)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "Category link"
        verbose_name_plural = "Category links"

    def __str__(self):
        return f"{self.category.name} - {self.title}"


class ClubSeason(TimeStampedModel):
    club = models.OneToOneField(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="current_season",
    )
    season = models.CharField(max_length=20)

    class Meta:
        ordering = ["club__name"]

    def __str__(self):
        return f"{self.club.name} - {self.season}"
