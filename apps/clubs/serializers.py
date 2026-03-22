from rest_framework import serializers
from .models import Club


class ClubSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = [
            "id",
            "name",
            "slug",
            "short_name",
            "description",
            "logo",
            "logo_url",
            "cover_image",
            "cover_image_url",
            "primary_color",
            "secondary_color",
            "accent_color",
            "email",
            "phone",
            "address",
            "city",
            "website_url",
            "facebook_url",
            "instagram_url",
            "youtube_url",
            "domain",
        ]

    def get_logo_url(self, obj):
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None

    def get_cover_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None