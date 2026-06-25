from django.contrib import admin

from .models import Partner
from .revalidation import revalidate_partner_paths


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "tier", "order", "is_active")
    list_filter = ("club", "tier", "is_active")
    search_fields = ("name", "club__name", "website", "logo_url")
    list_editable = ("order", "is_active")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        revalidate_partner_paths(obj, reason="Partner saved in Django admin")

    def delete_model(self, request, obj):
        partner = obj
        super().delete_model(request, obj)
        revalidate_partner_paths(partner, reason="Partner deleted in Django admin")
