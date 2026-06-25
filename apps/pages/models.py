from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


SECTION_CHOICES_BY_PAGE_TYPE = {
    "home": [
        "hero",
        "top_posts",
        "posts",
        "matches_overview",
        "next_match",
        "recent_matches",
        "standings",
        "partners",
        "poll",
        "recruitment",
        "links",
    ],
    "about": [
        "hero",
        "about_overview",
        "about_text",
        "achievements",
        "famous_players",
        "gallery",
        "contact",
        "links",
        "custom_text",
    ],
    "contact": [
        "hero",
        "contact",
        "documents",
        "links",
        "custom_text",
    ],
    "recruitment": [
        "hero",
        "benefits",
        "team_categories",
        "recruitment",
        "faq",
        "contact",
        "documents",
        "links",
        "custom_text",
    ],
    "category": [
        "hero",
        "next_match",
        "posts",
        "matches_overview",
        "leaders",
        "trainings",
        "recruitment",
        "links",
    ],
    "team_category": [
        "hero",
        "next_match",
        "posts",
        "matches_overview",
        "leaders",
        "trainings",
        "recruitment",
        "links",
    ],
    "articles": [
        "hero",
        "top_posts",
        "posts",
    ],
    "standard": [
        "hero",
        "custom_text",
        "about_text",
        "gallery",
        "contact",
        "documents",
        "links",
    ],
    "custom": [
        "hero",
        "custom_text",
        "about_text",
        "gallery",
        "contact",
        "documents",
        "links",
    ],
}


class Page(TimeStampedModel):
    PAGE_TYPE_CHOICES = [
        ("home", "Domov"),
        ("about", "O klube"),
        ("contact", "Kontakt"),
        ("recruitment", "Nábor / Pridaj sa"),
        ("category", "Kategória tímu"),
        ("articles", "Články"),
        ("custom", "Vlastná stránka"),
        ("standard", "Štandardná stránka"),
    ]

    MENU_GROUP_CHOICES = [
        ("hidden", "Nezobrazovať v menu"),
        ("main", "Hlavné menu"),
        ("youth", "Dropdown Mládež"),
        ("cta", "CTA tlačidlo"),
        ("footer", "Iba footer"),
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
    menu_group = models.CharField(
        max_length=20,
        choices=MENU_GROUP_CHOICES,
        default="hidden",
    )
    menu_group_title = models.CharField(max_length=120, blank=True)

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

        if self.is_homepage:
            self.page_type = "home"

    def get_public_path(self):
        if self.is_homepage or self.page_type == "home" or self.slug == "home":
            return "/"

        category_slugs = {
            "muzi",
            "pripravka",
            "mladsi-ziaci",
            "starsi-ziaci",
            "dorast",
            "juniori",
        }

        if self.page_type in {"category", "team_category"} or self.slug in category_slugs:
            return f"/kategorie/{self.slug}"

        if self.slug in {"pridaj_sa", "pridaj-sa"}:
            return "/pridaj_sa"

        if self.slug == "clanky" or self.page_type == "articles":
            return "/clanky"

        return f"/{self.slug}"

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
        ("leaders", "Lídri sezóny"),
        ("partners", "Partneri"),
        ("poll", "Anketa"),
        ("recruitment", "Nábor"),
        ("benefits", "Benefity"),
        ("team_categories", "Kategórie tímov"),
        ("faq", "Časté otázky"),
        ("trainings", "Tréningy"),
        ("links", "Klubové odkazy"),
        ("contact", "Kontakt"),
        ("documents", "Dokumenty"),
        ("gallery", "Galéria"),
        ("achievements", "Úspechy"),
        ("custom_text", "Vlastný text"),

        # O klube
        ("about_overview", "Prehľad o klube s mapou"),
        ("about_text", "Textová sekcia o klube"),
        ("famous_players", "Známi hráči / odchovanci"),
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

    def clean(self):
        super().clean()

        if not self.page_id:
            return

        allowed_sections = SECTION_CHOICES_BY_PAGE_TYPE.get(self.page.page_type)

        if allowed_sections and self.section_type not in allowed_sections:
            raise ValidationError({
                "section_type": (
                    f"Táto sekcia nie je povolená pre typ stránky "
                    f"„{self.page.get_page_type_display()}“."
                )
            })

    def __str__(self):
        return f"{self.page.title} - {self.get_section_type_display()}"


DEFAULT_SECTION_TEMPLATES = {
    "home": [
        ("hero", "", ""),
        ("top_posts", "Top obsah", "Najdôležitejšie novinky"),
        ("matches_overview", "Liga", "Výsledky"),
        ("posts", "Klubový obsah", "Ďalšie novinky a články"),
        ("next_match", "Program", "Najbližšie zápasy"),
        ("partners", "Partneri", "Podporujú náš klub"),
    ],
    "about": [
        ("hero", "O klube", ""),
        ("about_overview", "", "Príbeh ATU Košice"),
        ("achievements", "", "Klubové úspechy"),
        ("famous_players", "", "Hráči, na ktorých je klub hrdý"),
    ],
    "contact": [
        ("contact", "Kontakt", ""),
        ("documents", "Dokumenty", "Dôležité dokumenty"),
        ("links", "Odkazy", "Klubové odkazy"),
    ],
    "recruitment": [
        ("hero", "ATU Košice / Mládež", "Poď hrať florbal"),
        ("benefits", "", "Prečo ATU"),
        ("team_categories", "", "Kategórie"),
        ("faq", "FAQ", "Časté otázky"),
        ("contact", "Kontakt", "Príďte si vyskúšať tréning"),
    ],
    "articles": [
        ("hero", "", "Články"),
        ("posts", "", "Najnovšie články"),
    ],
    "category": [
        ("hero", "", ""),
        ("links", "SZFB", "Odkazy"),
        ("trainings", "Tréningy", "Kde trénujeme"),
        ("recruitment", "Nábor", ""),
        ("posts", "Aktuálne dianie", "Najdôležitejšie novinky"),
        ("next_match", "Zápasy", "Featured zápasy"),
        ("matches_overview", "Extraliga", "Výsledky"),
        ("leaders", "Štatistiky tímu", "Lídri sezóny"),
    ],
    "team_category": [
        ("hero", "", ""),
        ("links", "SZFB", "Odkazy"),
        ("trainings", "Tréningy", "Kde trénujeme"),
        ("recruitment", "Nábor", ""),
        ("posts", "Aktuálne dianie", "Najdôležitejšie novinky"),
        ("next_match", "Zápasy", "Featured zápasy"),
        ("matches_overview", "Extraliga", "Výsledky"),
        ("leaders", "Štatistiky tímu", "Lídri sezóny"),
    ],
}


def create_default_page_sections(page):
    if not page.pk or page.sections.exists():
        return False

    templates = DEFAULT_SECTION_TEMPLATES.get(page.page_type, [])

    if not templates:
        return False

    PageSection.objects.bulk_create(
        PageSection(
            page=page,
            section_type=section_type,
            pre_title=pre_title,
            title=title,
            order=index,
        )
        for index, (section_type, pre_title, title) in enumerate(templates, start=1)
    )
    return True
