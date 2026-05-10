from rest_framework import serializers
from .models import Partner
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPartnerSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "club",
            "club_name",
            "name",
            "logo",
            "logo_url",
            "image_url",
            "website",
            "tier",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")

        if obj.logo:
            logo_url = obj.logo.url
            if request:
                return request.build_absolute_uri(logo_url)
            return logo_url

        if obj.logo_url:
            return obj.logo_url

        return ""

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club