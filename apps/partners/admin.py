from django.contrib import admin
from .models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "tier", "order", "is_active")
    list_filter = ("club", "tier", "is_active")