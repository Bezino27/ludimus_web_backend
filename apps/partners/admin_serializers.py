from rest_framework import serializers

from apps.common.image_uploads import optimize_uploaded_image
from apps.common.permissions import EDITOR_ROLES, user_has_club_role

from .models import Partner



class AdminPartnerSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    image_url = serializers.SerializerMethodField()
    tier_label = serializers.CharField(read_only=True)
    public_tier = serializers.CharField(read_only=True)

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
            "tier_label",
            "public_tier",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "order",
            "created_at",
            "updated_at",
            "image_url",
            "tier_label",
            "public_tier",
        ]
        extra_kwargs = {
            "logo": {
                "required": False,
                "allow_null": True,
            },
            "logo_url": {
                "required": False,
                "allow_blank": True,
            },
            "website": {
                "required": False,
                "allow_blank": True,
            },
            "tier": {
                "required": False,
                "allow_blank": True,
            },
        }

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

    def validate_logo(self, logo):
        return optimize_uploaded_image(
            logo,
            "partner_logo",
            filename_prefix="partner-logo",
        )

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError(
                "Nemáš oprávnenie pre tento klub."
            )
        return club

    def validate(self, attrs):
        attrs = super().validate(attrs)

        current_logo = self.instance.logo if self.instance else None
        current_logo_url = self.instance.logo_url if self.instance else ""

        logo = attrs.get("logo", current_logo)
        logo_url = attrs.get("logo_url", current_logo_url)

        if not logo and not logo_url:
            raise serializers.ValidationError(
                {
                    "logo": (
                        "Nahraj logo alebo vyplň externú URL loga."
                    )
                }
            )

        return attrs