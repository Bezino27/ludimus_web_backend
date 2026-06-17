from rest_framework import serializers
from .models import ContactInfo, ClubDocument


class ContactInfoSerializer(serializers.ModelSerializer):
    club = serializers.SerializerMethodField()

    class Meta:
        model = ContactInfo
        fields = [
            "id",
            "club",
            "section_label",
            "title",
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
            "updated_at",
        ]

    def get_club(self, obj):
        return {
            "id": obj.club.id,
            "name": obj.club.name,
            "slug": obj.club.slug,
            "short_name": getattr(obj.club, "short_name", ""),
        }
    
class ClubDocumentSerializer(serializers.ModelSerializer):
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
            "updated_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")

        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)

        if obj.file:
            return obj.file.url

        return None