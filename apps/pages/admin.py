from django.contrib import admin
from .models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "is_published", "show_in_menu", "menu_order")
    list_filter = ("club", "is_published", "show_in_menu")
    prepopulated_fields = {"slug": ("title",)}