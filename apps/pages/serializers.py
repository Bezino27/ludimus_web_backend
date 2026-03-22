from rest_framework import serializers
from .models import Page


class PageSerializer(serializers.ModelSerializer):
    club_slug = serializers.CharField(source="club.slug", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "is_published",
            "show_in_menu",
            "menu_order",
            "meta_title",
            "meta_description",
            "club_slug",
            "created_at",
            "updated_at",
        ]