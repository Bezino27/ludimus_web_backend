from django.db import models
from apps.common.models import TimeStampedModel


class Category(TimeStampedModel):
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="categories"
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
        help_text="Krátky vizuálny názov kategórie, napr. MEX, U19, U17, U11-U9."
    )

    coach_name = models.CharField(max_length=150, blank=True)
    coach_email = models.EmailField(blank=True)
    coach_phone = models.CharField(max_length=30, blank=True)

    league_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Názov ligy zobrazovaný na webe, napr. Slovenská florbalová extraliga."
    )

    hero_image = models.ImageField(
        upload_to="categories/hero/",
        blank=True,
        null=True,
        help_text="Hlavná fotka kategórie zobrazovaná v hero sekcii na webe."
    )    

    class Meta:
        unique_together = ("club", "slug", "season")
        ordering = ["order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.club.name} - {self.name} ({self.season})"


class ClubSeason(TimeStampedModel):
    club = models.OneToOneField(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="current_season"
    )
    season = models.CharField(max_length=20)

    class Meta:
        ordering = ["club__name"]

    def __str__(self):
        return f"{self.club.name} - {self.season}"