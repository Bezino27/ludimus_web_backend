from rest_framework import serializers
from apps.club_info.serializers import ClubLinkSerializer
from .models import Club


class ClubSerializer(serializers.ModelSerializer):
    links = ClubLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "slug",
            "short_name",
            "description",
            "logo",
            "cover_image",
            "primary_color",
            "secondary_color",
            "accent_color",
            "links",
        ]
