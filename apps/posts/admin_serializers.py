from rest_framework import serializers

from .models import Post, PostCategory
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPostCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PostCategory
        fields = ["id", "name", "slug"]


class AdminPostSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)
    category_detail = AdminPostCategorySerializer(source="category", read_only=True)

    featured_image_url = serializers.SerializerMethodField(read_only=True)
    featured_image_path = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "club",
            "club_name",
            "category",
            "category_name",
            "category_detail",
            "author",
            "title",
            "slug",
            "excerpt",
            "content",
            "featured_image",
            "featured_image_url",
            "featured_image_path",
            "status",
            "published_at",
            "meta_title",
            "meta_description",
            "is_featured",
            "external_source",
            "external_id",
            "source_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "created_at", "updated_at", "featured_image"]

    def get_featured_image_url(self, obj):
        request = self.context.get("request")
        if obj.featured_image and request:
            return request.build_absolute_uri(obj.featured_image.url)
        return None

    def validate_club(self, club):
        request = self.context["request"]
        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise serializers.ValidationError("Nemáš oprávnenie pre tento klub.")
        return club

    def validate_featured_image_path(self, value):
        if value in [None, ""]:
            return value

        if not value.startswith("posts/featured/"):
            raise serializers.ValidationError("Neplatná cesta k featured obrázku.")

        return value

    def create(self, validated_data):
        featured_image_path = validated_data.pop("featured_image_path", None)
        validated_data["author"] = self.context["request"].user

        post = super().create(validated_data)

        if featured_image_path:
            post.featured_image = featured_image_path
            post.save(update_fields=["featured_image"])

        return post

    def update(self, instance, validated_data):
        featured_image_path = validated_data.pop("featured_image_path", None)

        post = super().update(instance, validated_data)

        if featured_image_path is not None:
            if featured_image_path == "":
                post.featured_image = None
            else:
                post.featured_image = featured_image_path
            post.save(update_fields=["featured_image"])

        return post