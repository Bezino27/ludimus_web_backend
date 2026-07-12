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
        "custom_documents",
        "links",
        "custom_links",
    ],
    "custom": [
        "hero",
        "custom_text",
        "contact",
        "gallery",
        "documents",
        "custom_documents",
        "links",
        "custom_links",
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

    team_category = models.ForeignKey(
        "teams.Category",
        on_delete=models.SET_NULL,
        related_name="pages",
        blank=True,
        null=True,
    )

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

        if (
            self.team_category_id
            and self.club_id
            and self.team_category.club_id != self.club_id
        ):
            raise ValidationError({
                "team_category": "Napojená kategória musí patriť rovnakému klubu."
            })

    @property
    def is_deletable(self):
        return self.page_type == "custom"

    def get_public_path(self):
        if self.is_homepage or self.page_type == "home" or self.slug == "home":
            return "/"

        if self.page_type == "about" or self.slug in {"o-klube", "about"}:
            return "/o-klube"

        if self.page_type == "contact" or self.slug == "kontakt":
            return "/kontakt"

        if self.page_type == "recruitment" or self.slug in {"pridaj_sa", "pridaj-sa"}:
            return "/pridaj_sa"

        if self.page_type == "category":
            return f"/kategorie/{self.slug}"

        category_slugs = {
            "muzi",
            "pripravka",
            "mladsi-ziaci",
            "starsi-ziaci",
            "dorast",
            "juniori",
        }

        if self.slug in category_slugs:
            return f"/kategorie/{self.slug}"

        if self.slug == "clanky" or self.page_type == "articles":
            return "/clanky"

        if self.page_type == "custom":
            return f"/stranka/{self.slug}"

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
        ("custom_links", "Vlastné odkazy"),
        ("contact", "Kontakt"),
        ("documents", "Klubové dokumenty"),
        ("custom_documents", "Vlastné dokumenty"),
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

    content = models.TextField(
        blank=True,
        help_text="Obsah pre textové sekcie, napr. Vlastný text.",
    )

    image = models.ImageField(
        upload_to="pages/sections/images/",
        blank=True,
        null=True,
        help_text="Voliteľný obrázok/banner najmä pre Hero sekciu.",
    )

    url = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "Staršie pole pre jednoduchý odkaz. "
            "Pre viac vlastných odkazov používaj položky sekcie."
        ),
    )

    file = models.FileField(
        upload_to="pages/sections/",
        blank=True,
        null=True,
        help_text=(
            "Staršie pole pre jeden súbor. "
            "Pre viac vlastných dokumentov používaj položky sekcie."
        ),
    )

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    hide_when_empty = models.BooleanField(default=False)

    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Voliteľné nastavenia vo formáte JSON. '
            'Pre klubové dokumenty napr. {"document_ids": [1, 2, 3]}. '
            'Pre klubové odkazy napr. {"link_ids": [1, 4, 7]}. '
            'Pre vlastné dokumenty a vlastné odkazy používaj položky sekcie.'
        ),
    )

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

    def save(self, *args, **kwargs):
        if self.section_type not in {"documents", "custom_documents"}:
            self.file = None

        if self.section_type != "hero":
            self.image = None

        if self.section_type not in {"links", "custom_links"}:
            self.url = ""

        super().save(*args, **kwargs)


class PageSectionContactItem(TimeStampedModel):
    CONTACT_TYPE_CHOICES = [
        ("phone", "Telefón"),
        ("email", "Email"),
        ("iban", "IBAN"),
        ("address", "Adresa"),
        ("person", "Osoba / kontaktná osoba"),
        ("web", "Web / URL"),
        ("text", "Text / poznámka"),
    ]

    section = models.ForeignKey(
        PageSection,
        on_delete=models.CASCADE,
        related_name="contact_items",
        limit_choices_to={"section_type": "contact"},
    )

    contact_type = models.CharField(
        max_length=30,
        choices=CONTACT_TYPE_CHOICES,
        default="text",
    )
    label = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Popis položky, napr. Telefón, Email, IBAN alebo Adresa.",
    )
    value = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Kontaktná položka sekcie"
        verbose_name_plural = "Kontaktné položky"

    def clean(self):
        super().clean()

        if not self.section_id:
            return

        if self.section.section_type != "contact":
            raise ValidationError({
                "section": "Kontaktné položky môžeš pridávať iba ku kontaktnej sekcii."
            })

        if not self.value and not self.url:
            raise ValidationError({
                "value": "Vyplň hodnotu alebo URL kontaktnej položky."
            })

        existing_items = self.section.contact_items.exclude(pk=self.pk).count()

        if existing_items >= 30:
            raise ValidationError("Jedna kontaktná sekcia môže mať najviac 30 položiek.")

    def save(self, *args, **kwargs):
        if self.contact_type != "web":
            self.url = ""

        if not self.label:
            self.label = self.get_contact_type_display()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.value or self.get_contact_type_display()


class PageSectionItem(TimeStampedModel):
    section = models.ForeignKey(
        PageSection,
        on_delete=models.CASCADE,
        related_name="items",
    )

    title = models.CharField(max_length=160)

    url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Používa sa pri sekcii Vlastné odkazy.",
    )

    file = models.FileField(
        upload_to="pages/sections/items/",
        blank=True,
        null=True,
        help_text="Používa sa pri sekcii Vlastné dokumenty.",
    )

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Položka sekcie"
        verbose_name_plural = "Položky sekcií"

    def clean(self):
        super().clean()

        if not self.section_id:
            return

        section_type = self.section.section_type

        if section_type == "custom_documents":
            if not self.file:
                raise ValidationError({"file": "Pri vlastnom dokumente nahraj súbor."})
            if self.url:
                raise ValidationError({
                    "url": "Vlastný dokument nepoužíva URL, nahraj súbor."
                })

        elif section_type == "custom_links":
            if not self.url:
                raise ValidationError({"url": "Pri vlastnom odkaze vyplň URL."})
            if self.file:
                raise ValidationError({
                    "file": "Vlastný odkaz nepoužíva súbor."
                })

        else:
            raise ValidationError(
                "Položky môžeš pridávať iba k sekciám Vlastné dokumenty alebo Vlastné odkazy."
            )

        existing_items = self.section.items.exclude(pk=self.pk).count()

        if existing_items >= 30:
            raise ValidationError("Jedna sekcia môže mať najviac 30 položiek.")

    def save(self, *args, **kwargs):
        if self.section_id:
            if self.section.section_type == "custom_documents":
                self.url = ""
            elif self.section.section_type == "custom_links":
                self.file = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


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
    "custom": [
        ("hero", "", ""),
        ("custom_text", "", ""),
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
