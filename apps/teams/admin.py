from django.contrib import admin

from .models import Category, ClubSeason
from .utils import recalculate_categories_for_club


@admin.register(ClubSeason)
class ClubSeasonAdmin(admin.ModelAdmin):
    list_display = (
        "club",
        "season",
        "updated_at",
    )
    list_filter = ("season",)
    search_fields = (
        "club__name",
        "club__slug",
        "season",
    )
    ordering = ("club__name",)

    def save_model(self, request, obj, form, change):
        old_season = None

        if change and obj.pk:
            old_season = ClubSeason.objects.filter(pk=obj.pk).values_list(
                "season",
                flat=True,
            ).first()

        super().save_model(request, obj, form, change)

        if old_season != obj.season:
            recalculate_categories_for_club(obj.club, obj.season)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "name",
        "club",
        "season",
        "category_subname",
        "league_name",
        "birth_year_from",
        "birth_year_to",
        "coach_name",
        "coach_email",
        "is_active",
    )
    list_display_links = ("name",)
    list_editable = (
        "order",
        "is_active",
    )
    list_filter = (
        "club",
        "season",
        "is_active",
    )
    search_fields = (
        "name",
        "slug",
        "club__name",
        "club__slug",
        "season",
        "category_subname",
        "league_name",
        "coach_name",
        "coach_email",
        "coach_phone",
    )
    ordering = (
        "club",
        "season",
        "order",
        "name",
    )
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (
            "Základné údaje",
            {
                "fields": (
                    "club",
                    "name",
                    "slug",
                    "season",
                    "order",
                    "is_active",
                )
            },
        ),
        (
            "Veková kategória",
            {
                "fields": (
                    "birth_year_from",
                    "birth_year_to",
                    "category_subname",
                )
            },
        ),
        (
            "Web",
            {
                "fields": (
                    "league_name",
                    "hero_image",
                )
            },
        ),
        (
            "Tréner",
            {
                "fields": (
                    "coach_name",
                    "coach_email",
                    "coach_phone",
                )
            },
        ),
    )