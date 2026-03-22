from django.contrib import admin
from .models import Match


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("club", "team", "opponent", "match_date", "competition", "is_published")
    list_filter = ("club", "team", "competition", "is_published")
    search_fields = ("opponent", "competition", "location")