from django.contrib import admin
from .models import GalleryAlbum, GalleryImage


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 1


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "is_published", "created_at")
    list_filter = ("club", "is_published")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [GalleryImageInline]