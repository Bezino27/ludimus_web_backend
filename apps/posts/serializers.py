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
            "created_at",
            "updated_at",
        ]
