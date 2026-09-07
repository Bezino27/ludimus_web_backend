from django.contrib import admin

from apps.common.revalidation import schedule_revalidation

from .models import (
    Category,
    CategoryLink,
    CategoryTraining,
    ClubSeason,
    TrainingLocation,
)
from .utils import recalculate_categories_for_club
from .revalidation import (
    get_category_child_revalidation_paths,
    get_category_revalidation_paths,
    get_club_season_revalidation_paths,
    get_training_location_revalidation_paths,
)


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
        schedule_revalidation(
            get_club_season_revalidation_paths(obj),
            reason="ClubSeason saved in Django admin",
            club_slug=obj.club.slug,
        )

    def delete_model(self, request, obj):
        paths = get_club_season_revalidation_paths(obj)
        club_slug = obj.club.slug
        super().delete_model(request, obj)
        schedule_revalidation(paths, reason="ClubSeason deleted in Django admin", club_slug=club_slug)


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

    def save_model(self, request, obj, form, change):
        old_slug = None
        if change and obj.pk:
            old_slug = Category.objects.filter(pk=obj.pk).values_list("slug", flat=True).first()
        super().save_model(request, obj, form, change)
        schedule_revalidation(
            get_category_revalidation_paths(obj, old_slug=old_slug),
            reason="Category saved in Django admin",
            club_slug=obj.club.slug,
        )

    def delete_model(self, request, obj):
        paths = get_category_revalidation_paths(obj)
        club_slug = obj.club.slug
        super().delete_model(request, obj)
        schedule_revalidation(paths, reason="Category deleted in Django admin", club_slug=club_slug)


@admin.register(TrainingLocation)
class TrainingLocationAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "club", "address", "latitude", "longitude", "is_active")
    list_display_links = ("name",)
    list_editable = ("order", "is_active")
    list_filter = ("club", "is_active")
    search_fields = ("name", "address", "club__name", "club__slug")
    ordering = ("club", "order", "name")

    def save_model(self, request, obj, form, change):
        old_paths = get_training_location_revalidation_paths(obj) if change else []
        super().save_model(request, obj, form, change)
        schedule_revalidation(
            [*old_paths, *get_training_location_revalidation_paths(obj)],
            reason="TrainingLocation saved in Django admin",
            club_slug=obj.club.slug,
        )

    def delete_model(self, request, obj):
        paths = get_training_location_revalidation_paths(obj)
        club_slug = obj.club.slug
        super().delete_model(request, obj)
        schedule_revalidation(paths, reason="TrainingLocation deleted in Django admin", club_slug=club_slug)


@admin.register(CategoryTraining)
class CategoryTrainingAdmin(admin.ModelAdmin):
    list_display = ("category", "weekday", "start_time", "location", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("category__club", "weekday", "is_active")
    search_fields = ("category__name", "location__name")
    ordering = ("category", "order", "weekday", "start_time")

    def save_model(self, request, obj, form, change):
        old_category = None
        if change and obj.pk:
            previous = CategoryTraining.objects.select_related("category").filter(pk=obj.pk).first()
            old_category = previous.category if previous else None
        super().save_model(request, obj, form, change)
        schedule_revalidation(
            [
                *get_category_child_revalidation_paths(old_category),
                *get_category_child_revalidation_paths(obj.category),
            ],
            reason="CategoryTraining saved in Django admin",
            club_slug=obj.category.club.slug,
        )

    def delete_model(self, request, obj):
        category = obj.category
        super().delete_model(request, obj)
        schedule_revalidation(
            get_category_child_revalidation_paths(category),
            reason="CategoryTraining deleted in Django admin",
            club_slug=category.club.slug,
        )


@admin.register(CategoryLink)
class CategoryLinkAdmin(admin.ModelAdmin):
    list_display = ("category", "title", "order", "is_active")
    list_editable = ("order", "is_active")
    list_filter = ("category__club", "is_active")
    search_fields = ("category__name", "title", "description", "url")
    ordering = ("category", "order", "title")

    def save_model(self, request, obj, form, change):
        old_category = None
        if change and obj.pk:
            previous = CategoryLink.objects.select_related("category").filter(pk=obj.pk).first()
            old_category = previous.category if previous else None
        super().save_model(request, obj, form, change)
        schedule_revalidation(
            [
                *get_category_child_revalidation_paths(old_category),
                *get_category_child_revalidation_paths(obj.category),
            ],
            reason="CategoryLink saved in Django admin",
            club_slug=obj.category.club.slug,
        )

    def delete_model(self, request, obj):
        category = obj.category
        super().delete_model(request, obj)
        schedule_revalidation(
            get_category_child_revalidation_paths(category),
            reason="CategoryLink deleted in Django admin",
            club_slug=category.club.slug,
        )
