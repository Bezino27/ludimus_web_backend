from django.contrib import admin

from .models import Poll, PollOption, PollVote


class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 2
    fields = ("text", "order")


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "club",
        "question",
        "admin_enabled",
        "is_currently_open",
        "starts_at",
        "ends_at",
        "created_at",
    )
    list_filter = ("club", "is_active", "created_at", "starts_at", "ends_at")
    search_fields = ("question", "description", "club__name", "club__slug")
    ordering = ("-created_at",)
    inlines = [PollOptionInline]

    fieldsets = (
        (
            "Základné údaje",
            {
                "fields": (
                    "question",
                    "club",
                    "description",
                )
            },
        ),
        (
            "Aktivita ankety",
            {
                "fields": (
                    "is_active",
                    "starts_at",
                    "ends_at",
                ),
                "description": (
                    "is_active je ručný vypínač ankety. "
                    "Ak je zapnutý, anketa sa reálne otvorí podľa starts_at "
                    "a automaticky skončí podľa ends_at."
                ),
            },
        ),
    )

    @admin.display(boolean=True, description="Povolená")
    def admin_enabled(self, obj):
        return obj.is_active

    @admin.display(boolean=True, description="Voting open")
    def is_currently_open(self, obj):
        return obj.is_open_for_voting


@admin.register(PollOption)
class PollOptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "poll",
        "text",
        "order",
        "created_at",
    )
    list_filter = ("poll",)
    search_fields = ("text", "poll__question")
    ordering = ("poll", "order", "id")


@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "poll",
        "option",
        "voter_id",
        "user_agent_hash",
        "created_at",
    )
    list_filter = ("poll", "option", "created_at")
    search_fields = ("poll__question", "option__text", "voter_id")
    readonly_fields = (
        "poll",
        "option",
        "voter_id",
        "user_agent_hash",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False
