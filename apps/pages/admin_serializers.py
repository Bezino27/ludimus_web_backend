from rest_framework import serializers

from .models import Page
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPageSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "club",
            "club_name",
            "title",
            "slug",
            "content",
            "is_published",
            "show_in_menu",
            "menu_order",
            "meta_title",
            "meta_description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club