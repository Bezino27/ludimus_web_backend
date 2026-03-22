from django.contrib import admin
from .models import Team, TeamMember


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "season", "is_active")
    list_filter = ("club", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "club", "team", "role", "is_active")
    list_filter = ("club", "role", "is_active")
    search_fields = ("first_name", "last_name")