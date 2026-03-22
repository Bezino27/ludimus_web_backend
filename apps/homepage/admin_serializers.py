from rest_framework import serializers
from .models import HomepageSection
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminHomepageSectionSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = HomepageSection
        fields = [
            "id",
            "club",
            "club_name",
            "title",
            "subtitle",
            "content",
            "image",
            "button_text",
            "button_link",
            "order",
            "is_active",
        ]

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club