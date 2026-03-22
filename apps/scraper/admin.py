from django.contrib import admin
from .models import ScraperSource, ScraperJob


@admin.register(ScraperSource)
class ScraperSourceAdmin(admin.ModelAdmin):
    list_display = ("club", "name", "source_type", "is_active")
    list_filter = ("club", "source_type", "is_active")


@admin.register(ScraperJob)
class ScraperJobAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "created_at")
    list_filter = ("status",)