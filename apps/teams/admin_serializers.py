from rest_framework import serializers

from .models import Category


class AdminCategorySerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "club",
            "club_name",
            "season",
            "category_subname",
            "order",
            "is_active",
        ]
