from rest_framework import serializers
from .models import Category, ClubSeason


def format_display_years(category):
    min_year = min(category.birth_year_from, category.birth_year_to)
    max_year = max(category.birth_year_from, category.birth_year_to)
    slug = (category.slug or "").lower()

    if slug == "muzi":
        return f"> {max_year}"

    if slug == "pripravka":
        return f"< {min_year}"

    if min_year == max_year:
        return str(min_year)

    return f"{min_year}-{max_year}"

class CategorySerializer(serializers.ModelSerializer):
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "club",
            "name",
            "slug",
            "season",
            "birth_year_from",
            "birth_year_to",
            "category_subname",
            "display_years",
            "league_name",
            "hero_image_url",
            "order",
            "is_active",
            "coach_name",
            "coach_email",
            "coach_phone",
        ]

    def get_display_years(self, obj):
        return format_display_years(obj)

    def get_hero_image_url(self, obj):
        request = self.context.get("request")

        if obj.hero_image:
            if request:
                return request.build_absolute_uri(obj.hero_image.url)
            return obj.hero_image.url

        return None


class CategoryBirthYearsSerializer(serializers.ModelSerializer):
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "season",
            "birth_year_from",
            "birth_year_to",
            "category_subname",
            "display_years",
            "league_name",
            "hero_image_url",
            "coach_name",
            "coach_email",
            "coach_phone",
        ]

    def get_display_years(self, obj):
        return format_display_years(obj)

    def get_hero_image_url(self, obj):
        request = self.context.get("request")

        if obj.hero_image:
            if request:
                return request.build_absolute_uri(obj.hero_image.url)
            return obj.hero_image.url

        return None

class ClubSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSeason
        fields = [
            "id",
            "club",
            "season",
        ]