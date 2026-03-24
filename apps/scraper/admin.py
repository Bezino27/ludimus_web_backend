from django.contrib import admin
from .models import SzfbCompetition, SzfbStandingRow, SzfbTeamWatch, SzfbMatch


@admin.register(SzfbCompetition)
class SzfbCompetitionAdmin(admin.ModelAdmin):
    list_display = ("id", "szfb_competition_id", "name", "season", "last_synced_at")
    search_fields = ("name", "season", "szfb_competition_id")


@admin.register(SzfbStandingRow)
class SzfbStandingRowAdmin(admin.ModelAdmin):
    list_display = ("competition", "position", "team_name", "played", "points")
    list_filter = ("competition",)
    search_fields = ("team_name",)


@admin.register(SzfbTeamWatch)
class SzfbTeamWatchAdmin(admin.ModelAdmin):
    list_display = ("label", "competition", "team_name", "is_active")
    list_filter = ("competition", "is_active")
    search_fields = ("label", "team_name")


@admin.register(SzfbMatch)
class SzfbMatchAdmin(admin.ModelAdmin):
    list_display = (
        "watched_team",
        "match_type",
        "match_date",
        "match_time",
        "opponent",
        "result",
        "venue",
        "is_home",
    )
    list_filter = ("watched_team", "match_type")
    search_fields = ("opponent", "venue", "result")