from rest_framework import serializers

from .models import ContactInfo, ClubDocument, ClubLink


class AdminContactInfoSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)

    class Meta:
        model = ContactInfo
        fields = [
            "id",
            "club_name",
            "club_slug",
            "address",
            "chairman_name",
            "email",
            "phone",
            "iban",
            "map_label",
            "map_address",
            "latitude",
            "longitude",
            "note",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "club_name", "club_slug", "created_at", "updated_at"]


class AdminClubDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ClubDocument
        fields = [
            "id",
            "title",
            "file",
            "file_url",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "file_url", "created_at", "updated_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")

        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)

        if obj.file:
            return obj.file.url

        return None


class AdminClubLinkSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = ClubLink
        fields = [
            "id",
            "title",
            "url",
            "icon_type",
            "logo",
            "logo_url",
            "order",
            "is_active",
        ]
        read_only_fields = ["id", "logo_url"]

    def get_logo_url(self, obj):
        request = self.context.get("request")

        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)

        if obj.logo:
            return obj.logo.url

        return None
