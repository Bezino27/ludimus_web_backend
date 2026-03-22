from rest_framework import serializers
from .models import GalleryAlbum, GalleryImage
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminGalleryImageSerializer(serializers.ModelSerializer):
    album_title = serializers.CharField(source="album.title", read_only=True)

    class Meta:
        model = GalleryImage
        fields = [
            "id",
            "album",
            "album_title",
            "image",
            "caption",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_album(self, album):
        request = self.context["request"]
        if not user_has_club_role(request.user, album.club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento album.")
        return album


class AdminGalleryAlbumSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    images = AdminGalleryImageSerializer(many=True, read_only=True)

    class Meta:
        model = GalleryAlbum
        fields = [
            "id",
            "club",
            "club_name",
            "title",
            "slug",
            "description",
            "cover_image",
            "is_published",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club