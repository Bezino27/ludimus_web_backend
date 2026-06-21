from django.contrib import admin
from .models import ContactInfo, ClubDocument, ClubLink


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("club", "title", "email", "phone", "is_active", "updated_at")
    list_filter = ("is_active", "club")
    search_fields = ("club__name", "title", "address", "email", "phone")
    readonly_fields = ("created_at", "updated_at")

@admin.register(ClubDocument)
class ClubDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "order", "is_active", "updated_at")
    list_filter = ("is_active", "club")
    search_fields = ("title", "club__name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("order", "title")


@admin.register(ClubLink)
class ClubLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "url", "icon_type", "order", "is_active")
    list_filter = ("club", "icon_type", "is_active")
    search_fields = ("title", "url", "club__name")
    ordering = ("club", "order", "title")
    fields = ("club", "title", "url", "icon_type", "logo", "order", "is_active")
