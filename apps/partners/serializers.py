from rest_framework import serializers
from .models import Partner


class PartnerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "logo",
            "logo_url",
            "image_url",
            "website",
            "tier",
            "order",
            "is_active",
        ]

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