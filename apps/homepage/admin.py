from django.contrib import admin
from .models import HomepageSection


@admin.register(HomepageSection)
class HomepageSectionAdmin(admin.ModelAdmin):
    list_display = ("club", "section_type", "title", "is_active", "order")
    list_filter = ("club", "section_type", "is_active")