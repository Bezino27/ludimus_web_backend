from rest_framework import serializers
from .models import Partner
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPartnerSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = Partner
        fields = [
            "id",
            "club",
            "club_name",
            "name",
            "logo",
            "website",
            "tier",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club