from django.contrib import admin

from .models import (
    Category,
    CategoryLink,
    CategoryTraining,
    ClubSeason,
    TrainingLocation,
)
from .utils import recalculate_categories_for_club


class CategoryTrainingInline(admin.TabularInline):
    model = CategoryTraining
    extra = 0
    fields = ("weekday", "start_time", "location", "order", "is_active")


class CategoryLinkInline(admin.TabularInline):
    model = CategoryLink
    extra = 0
    fields = ("title", "description", "cta_text", "url", "order", "is_active")


@admin.register(ClubSeason)
class ClubSeasonAdmin(admin.ModelAdmin):
    list_display = ("club", "season", "updated_at")
    list_filter = ("season",)
    search_fields = ("club__name", "club__slug", "season")
    ordering = ("club__name",)

    def save_model(self, request, obj, form, change):
        old_season = None
        if change and obj.pk:
            old_season = ClubSeason.objects.filter(pk=obj.pk).values_list(
                "season", flat=True
            ).first()

        super().save_model(request, obj, form, change)

        if old_season != obj.season:
            recalculate_categories_for_club(obj.club, obj.season)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "order", "name", "club", "season", "category_subname", "league_name",
        "birth_year_from", "birth_year_to", "coach_name", "coach_email", "is_active",
    )
    list_display_links = ("name",)
    list_editable = ("order", "is_active")
    list_filter = ("club", "season", "is_active")
    search_fields = (
        "name", "slug", "club__name", "club__slug", "season", "category_subname",
        "league_name", "coach_name", "coach_email", "coach_phone",
    )
    ordering = ("club", "season", "order", "name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CategoryTrainingInline, CategoryLinkInline]

    fieldsets = (
        ("Základné údaje", {"fields": ("club", "name", "slug", "season", "order", "is_active")}),
        ("Veková kategória", {"fields": ("birth_year_from", "birth_year_to", "category_subname")}),
        ("Web", {"fields": ("league_name", "hero_image", "szfb_team_watch")}),
        ("Tréner", {"fields": ("coach_name", "coach_email", "coach_phone")}),
    )


@admin.register(TrainingLocation)
class TrainingLocationAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "club", "address", "latitude", "longitude", "is_active")
    list_display_links = ("name",)
    list_editable = ("order", "is_active")
    list_filter = ("club", "is_active")
    search_fields = ("name", "address", "club__name", "club__slug")
    ordering = ("club", "order", "name")


@admin.register(CategoryTraining)
class CategoryTrainingAdmin(admin.ModelAdmin):
    list_display = ("category", "weekday", "start_time", "location", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("category__club", "weekday", "is_active")
    search_fields = ("category__name", "location__name")
    ordering = ("category", "order", "weekday", "start_time")


@admin.register(CategoryLink)
class CategoryLinkAdmin(admin.ModelAdmin):
    list_display = ("category", "title", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("category__club", "is_active")
    search_fields = ("category__name", "title", "description", "url")
    ordering = ("category", "order", "title")