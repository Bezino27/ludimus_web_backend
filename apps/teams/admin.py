from django.contrib import admin
from .models import Category, ClubSeason
from .utils import recalculate_categories_for_club


@admin.register(ClubSeason)
class ClubSeasonAdmin(admin.ModelAdmin):
    list_display = ("club", "season")
    search_fields = ("club__name", "season")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        recalculate_categories_for_club(obj.club, obj.season)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
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
    list_filter = ("club", "season", "is_active")
    search_fields = (
        "name",
        "slug",
        "club__name",
        "season",
        "category_subname",
        "league_name",
        "coach_name",
        "coach_email",
    )
    ordering = ("club", "order", "name")
    prepopulated_fields = {"slug": ("name",)}