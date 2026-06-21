from django.contrib import admin
from .models import Club, ClubMembership


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    fields = (
        "name",
        "slug",
        "short_name",
        "description",
        "logo",
        "cover_image",
        "primary_color",
        "secondary_color",
        "accent_color",
    )
    list_display = ("name", "slug", "short_name", "is_active")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("name", "slug", "short_name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "role", "is_active")
    list_filter = ("role", "is_active", "club")
    search_fields = ("user__username", "club__name")
