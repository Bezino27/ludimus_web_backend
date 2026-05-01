from rest_framework import serializers
from .models import Category, ClubSeason


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class CategoryBirthYearsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "season",
            "description",
            "birth_year_from",
            "birth_year_to",
            "coach_name",
            "coach_email",
            "coach_phone",
        ]


class ClubSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSeason
        fields = [
            "id",
            "club",
            "season",
        ]