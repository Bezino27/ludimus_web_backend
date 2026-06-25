from rest_framework import serializers

from .models import Page, PageSection
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPageSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageSection
        fields = [
            "id",
            "page",
            "section_type",
            "title",
            "pre_title",
            "order",
            "is_active",
            "hide_when_empty",
            "config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AdminPageSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    public_path = serializers.CharField(source="get_public_path", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "club",
            "club_name",
            "title",
            "slug",
            "menu_title",
            "page_type",
            "is_homepage",
            "is_published",
            "show_in_header",
            "show_in_footer",
            "navigation_order",
            "menu_group",
            "menu_group_title",
            "public_path",
            "meta_title",
            "meta_description",
            "og_image",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "public_path"]

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club
