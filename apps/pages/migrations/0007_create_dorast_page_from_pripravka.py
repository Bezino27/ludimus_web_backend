# Generated manually to seed the Dorast page from Pripravka.

from copy import deepcopy

from django.db import migrations


DORAST_PAGE_DEFAULTS = {
    "title": "Dorast",
    "slug": "dorast",
    "menu_title": "Dorast",
    "navigation_order": 4,
    "meta_title": "Dorast",
}


def create_dorast_pages(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    PageSection = apps.get_model("pages", "PageSection")

    source_pages = Page.objects.filter(slug="pripravka").select_related("club")

    for source_page in source_pages:
        dorast_page, _created = Page.objects.get_or_create(
            club=source_page.club,
            slug=DORAST_PAGE_DEFAULTS["slug"],
            defaults={
                "title": DORAST_PAGE_DEFAULTS["title"],
                "menu_title": DORAST_PAGE_DEFAULTS["menu_title"],
                "page_type": source_page.page_type,
                "is_homepage": False,
                "is_published": source_page.is_published,
                "show_in_footer": source_page.show_in_footer,
                "navigation_order": DORAST_PAGE_DEFAULTS["navigation_order"],
                "menu_group": source_page.menu_group,
                "menu_group_title": source_page.menu_group_title or "Mládež",
                "meta_title": DORAST_PAGE_DEFAULTS["meta_title"],
                "meta_description": source_page.meta_description,
                "og_image": source_page.og_image,
            },
        )

        if dorast_page.sections.exists():
            continue

        source_sections = list(source_page.sections.order_by("order", "id"))

        if not source_sections:
            continue

        PageSection.objects.bulk_create(
            PageSection(
                page=dorast_page,
                section_type=section.section_type,
                pre_title=section.pre_title,
                title=section.title,
                order=section.order,
                is_active=section.is_active,
                hide_when_empty=section.hide_when_empty,
                config=deepcopy(section.config),
            )
            for section in source_sections
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0006_page_menu_group_page_menu_group_title_and_more"),
    ]

    operations = [
        migrations.RunPython(create_dorast_pages, noop_reverse),
    ]
