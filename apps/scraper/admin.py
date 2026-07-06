from django.contrib import admin

from .models import (
    ClubPlayer,
    SzfbAutoSyncConfig,
    SzfbCompetition,
    SzfbStandingRow,
    SzfbTeamWatch,
    SzfbMatch,
    SzfbPlayerStat,
)


@admin.register(SzfbCompetition)
class SzfbCompetitionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "szfb_competition_id",
        "name",
        "season",
        "sync_status",
        "last_synced_at",
        "sync_finished_at",
    )
    search_fields = (
        "name",
        "season",
        "szfb_competition_id",
    )
    list_filter = (
        "sync_status",
        "season",
    )


@admin.register(SzfbAutoSyncConfig)
class SzfbAutoSyncConfigAdmin(admin.ModelAdmin):
    list_display = (
        "club",
        "is_enabled",
        "frequency",
        "weekday",
        "run_time",
        "last_run_at",
        "next_run_at",
        "last_status",
        "updated_at",
    )
    list_filter = (
        "is_enabled",
        "frequency",
        "weekday",
        "last_status",
    )
    search_fields = (
        "club__name",
        "club__slug",
        "last_message",
    )
    readonly_fields = (
        "last_run_at",
        "next_run_at",
        "last_status",
        "last_message",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Nastavenie automatiky",
            {
                "fields": (
                    "club",
                    "is_enabled",
                    "frequency",
                    "weekday",
                    "run_time",
                )
            },
        ),
        (
            "Stav",
            {
                "fields": (
                    "last_run_at",
                    "next_run_at",
                    "last_status",
                    "last_message",
                )
            },
        ),
        (
            "Systémové údaje",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    ordering = (
        "club__name",
    )


@admin.register(SzfbStandingRow)
class SzfbStandingRowAdmin(admin.ModelAdmin):
    list_display = (
        "competition",
        "position",
        "team_name",
        "played",
        "points",
    )
    list_filter = (
        "competition",
    )
    search_fields = (
        "team_name",
    )


@admin.register(SzfbTeamWatch)
class SzfbTeamWatchAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "club",
        "competition",
        "team_name",
        "competitor_id",
        "is_active",
    )
    list_filter = (
        "club",
        "competition",
        "is_active",
    )
    search_fields = (
        "label",
        "team_name",
        "competitor_id",
    )


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
    list_filter = (
        "watched_team",
        "match_type",
    )
    search_fields = (
        "opponent",
        "venue",
        "result",
    )


@admin.register(ClubPlayer)
class ClubPlayerAdmin(admin.ModelAdmin):
    list_display = (
        "club",
        "full_name",
        "birth_year",
        "jersey_number",
        "position",
        "height_cm",
        "weight_kg",
        "is_active",
        "is_featured",
        "display_order",
        "updated_at",
    )
    list_filter = (
        "club",
        "is_active",
        "is_featured",
        "position",
    )
    search_fields = (
        "full_name",
        "normalized_name",
        "identity_key",
    )
    readonly_fields = (
        "normalized_name",
        "identity_key",
        "created_at",
        "updated_at",
    )
    ordering = (
        "club",
        "display_order",
        "full_name",
    )


@admin.register(SzfbPlayerStat)
class SzfbPlayerStatAdmin(admin.ModelAdmin):
    list_display = (
        "watched_team",
        "club_player",
        "rank",
        "player_name",
        "birth_year",
        "team_short_name",
        "player_position",
        "jersey_number",
        "is_active",
        "is_featured",
        "display_order",
        "games",
        "goals",
        "assists",
        "points",
    )

    list_filter = (
        "watched_team",
        "player_position",
        "is_active",
        "is_featured",
    )

    search_fields = (
        "player_name",
        "team_short_name",
        "club_player__full_name",
    )

    fieldsets = (
        (
            "SZFB údaje",
            {
                "fields": (
                    "watched_team",
                    "club_player",
                    "rank",
                    "player_name",
                    "birth_year",
                    "team_short_name",
                    "player_position",
                    "games",
                    "goals",
                    "assists",
                    "points",
                    "points_avg",
                    "esp",
                    "ppp",
                    "shp",
                    "pim",
                )
            },
        ),
        (
            "Dočasné staré klubové údaje",
            {
                "fields": (
                    "photo",
                    "jersey_number",
                    "bio",
                    "is_active",
                    "is_featured",
                    "display_order",
                )
            },
        ),
    )

    ordering = (
        "watched_team",
        "display_order",
        "rank",
    )