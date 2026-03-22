from django.contrib import admin
from .models import Club, ClubMembership


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "email", "city", "is_active")
    search_fields = ("name", "slug", "email", "city")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "role", "is_active")
    list_filter = ("role", "is_active", "club")
    search_fields = ("user__username", "club__name")