from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class Page(TimeStampedModel):
    PAGE_TYPE_CHOICES = [
        ("standard", "Štandardná stránka"),
        ("home", "Domovská stránka"),
        ("about", "O klube"),
        ("contact", "Kontakt"),
        ("recruitment", "Nábor"),
        ("category", "Kategória"),
        ("articles", "Články"),
        ("custom", "Vlastná stránka"),
    ]

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="pages",
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField()

    menu_title = models.CharField(max_length=120, blank=True)

    page_type = models.CharField(
        max_length=30,
        choices=PAGE_TYPE_CHOICES,
        default="standard",
    )

    is_homepage = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    show_in_header = models.BooleanField(default=False)
    show_in_footer = models.BooleanField(default=False)
    navigation_order = models.PositiveIntegerField(default=0)

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    og_image = models.ImageField(upload_to="pages/og/", blank=True, null=True)

    class Meta:
        unique_together = ("club", "slug")
        ordering = ["navigation_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["club"],
                condition=Q(is_homepage=True),
                name="unique_homepage_per_club",
            )
        ]

    def clean(self):
        super().clean()

        if self.is_homepage and self.page_type != "home":
            self.page_type = "home"

    def __str__(self):
        return f"{self.club.name} - {self.title}"


class PageSection(TimeStampedModel):
    SECTION_TYPE_CHOICES = [
        ("hero", "Hero"),
        ("top_posts", "Najdôležitejšie novinky"),
        ("posts", "Články / novinky"),
        ("matches_overview", "Zápasy + tabuľka"),
        ("next_match", "Najbližší zápas"),
        ("recent_matches", "Posledné zápasy"),
        ("standings", "Tabuľka"),
        ("partners", "Partneri"),
        ("poll", "Anketa"),
        ("recruitment", "Nábor"),
        ("links", "Klubové odkazy"),
        ("contact", "Kontakt"),
        ("documents", "Dokumenty"),
        ("gallery", "Galéria"),
        ("achievements", "Úspechy"),
        ("custom_text", "Vlastný text"),
    ]

    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    section_type = models.CharField(
        max_length=50,
        choices=SECTION_TYPE_CHOICES,
    )

    pre_title = models.CharField(max_length=120, blank=True)
    title = models.CharField(max_length=160, blank=True)

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    hide_when_empty = models.BooleanField(default=False)

    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Sekcia stránky"
        verbose_name_plural = "Sekcie stránok"

    def __str__(self):
        return f"{self.page.title} - {self.get_section_type_display()}"
