from django.contrib import admin

from apps.common.revalidation import revalidate_paths

from .models import ContactInfo, ClubDocument, ClubLink


def revalidate_contact_paths(obj, reason):
    club_slug = getattr(getattr(obj, "club", None), "slug", "")
    revalidate_paths(["/kontakt"], reason=reason, club_slug=club_slug)


def revalidate_club_link_paths(obj, reason):
    club_slug = getattr(getattr(obj, "club", None), "slug", "")
    revalidate_paths(["/", "/kontakt", "/o-klube"], reason=reason, club_slug=club_slug)


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("club", "title", "email", "phone", "is_active", "updated_at")
    list_filter = ("is_active", "club")
    search_fields = ("club__name", "title", "address", "email", "phone")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        revalidate_contact_paths(obj, reason="ContactInfo saved in Django admin")

    def delete_model(self, request, obj):
        contact = obj
        super().delete_model(request, obj)
        revalidate_contact_paths(contact, reason="ContactInfo deleted in Django admin")


@admin.register(ClubDocument)
class ClubDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "order", "is_active", "updated_at")
    list_filter = ("is_active", "club")
    search_fields = ("title", "club__name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("order", "title")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        revalidate_contact_paths(obj, reason="ClubDocument saved in Django admin")

    def delete_model(self, request, obj):
        document = obj
        super().delete_model(request, obj)
        revalidate_contact_paths(document, reason="ClubDocument deleted in Django admin")


@admin.register(ClubLink)
class ClubLinkAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "url", "icon_type", "order", "is_active")
    list_filter = ("club", "icon_type", "is_active")
    search_fields = ("title", "url", "club__name")
    ordering = ("club", "order", "title")
    fields = ("club", "title", "url", "icon_type", "logo", "order", "is_active")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        revalidate_club_link_paths(obj, reason="ClubLink saved in Django admin")

    def delete_model(self, request, obj):
        link = obj
        super().delete_model(request, obj)
        revalidate_club_link_paths(link, reason="ClubLink deleted in Django admin")
