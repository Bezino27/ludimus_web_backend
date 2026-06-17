from django.contrib import admin
from .models import ContactInfo, ClubDocument


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