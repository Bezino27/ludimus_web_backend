from rest_framework import serializers
from .models import Post, PostCategory


class PostCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PostCategory
        fields = ["id", "name", "slug"]


class PostListSerializer(serializers.ModelSerializer):
    category = PostCategorySerializer(read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "featured_image",
            "published_at",
            "updated_at",
            "is_featured",
            "category",
            "club_slug",
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    category = PostCategorySerializer(read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_first_name = serializers.CharField(source="author.first_name", read_only=True)
    author_last_name = serializers.CharField(source="author.last_name", read_only=True)
    author_name = serializers.SerializerMethodField()
    published_at = serializers.SerializerMethodField()

    def get_author_name(self, obj):
        if not obj.author:
            return ""

        full_name = f"{obj.author.last_name} {obj.author.first_name}".strip()
        return full_name or obj.author.username

    def get_published_at(self, obj):
        value = obj.published_at or obj.created_at
        return serializers.DateTimeField().to_representation(value)

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "featured_image",
            "published_at",
            "status",
            "meta_title",
            "meta_description",
            "is_featured",
            "category",
            "club_slug",
            "author_username",
            "author_first_name",
            "author_last_name",
            "author_name",
            "created_at",
            "updated_at",
        ]
