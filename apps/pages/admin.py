from django.contrib import admin

from .models import Page, PageSection


class PageSectionInline(admin.TabularInline):
    model = PageSection
    extra = 1
    fields = (
        "section_type",
        "pre_title",
        "title",
        "order",
        "is_active",
        "hide_when_empty",
        "config",
    )


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "club",
        "page_type",
        "is_homepage",
        "is_published",
        "show_in_header",
        "show_in_footer",
        "navigation_order",
    )
    list_filter = (
        "club",
        "page_type",
        "is_homepage",
        "is_published",
        "show_in_header",
        "show_in_footer",
    )
    search_fields = ("title", "menu_title", "slug", "club__name")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [PageSectionInline]

    fieldsets = (
        ("Základné údaje", {
            "fields": (
                "club",
                "title",
                "slug",
                "menu_title",
                "page_type",
                "is_homepage",
                "is_published",
            )
        }),
        ("Navigácia", {
            "fields": (
                "show_in_header",
                "show_in_footer",
                "navigation_order",
            )
        }),
        ("SEO", {
            "fields": (
                "meta_title",
                "meta_description",
                "og_image",
            )
        }),
    )


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    list_display = (
        "page",
        "section_type",
        "title",
        "order",
        "is_active",
        "hide_when_empty",
    )
    list_filter = (
        "section_type",
        "is_active",
        "hide_when_empty",
        "page__club",
    )
    search_fields = (
        "page__title",
        "title",
    )
    ordering = (
        "page__club",
        "page",
        "order",
    )
