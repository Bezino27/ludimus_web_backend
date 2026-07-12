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


def normalize_text(value):
    if not value:
        return ""

    import unicodedata
    import re

    value = unicodedata.normalize("NFD", str(value))
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def get_category_szfb_watch(category):
    return getattr(category, "szfb_team_watch", None)


class CategorySerializer(serializers.ModelSerializer):
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    szfb_team_watch_id = serializers.SerializerMethodField()
    szfb_team_watch_label = serializers.SerializerMethodField()
    szfb_team_watch_competition_name = serializers.SerializerMethodField()
    szfb_team_watch_competition_season = serializers.SerializerMethodField()
    szfb_watch_id = serializers.SerializerMethodField()
    szfb_watch_label = serializers.SerializerMethodField()
    szfb_competition_name = serializers.SerializerMethodField()

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
            "szfb_team_watch_id",
            "szfb_team_watch_label",
            "szfb_team_watch_competition_name",
            "szfb_team_watch_competition_season",
            "szfb_watch_id",
            "szfb_watch_label",
            "szfb_competition_name",
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

    def get_szfb_team_watch_id(self, obj):
        watch = get_category_szfb_watch(obj)
        return watch.id if watch else None

    def get_szfb_team_watch_label(self, obj):
        watch = get_category_szfb_watch(obj)
        return getattr(watch, "label", None) if watch else None

    def get_szfb_team_watch_competition_name(self, obj):
        watch = get_category_szfb_watch(obj)

        if not watch:
            return None

        competition = getattr(watch, "competition", None)
        return getattr(competition, "name", None) if competition else None

    def get_szfb_team_watch_competition_season(self, obj):
        watch = get_category_szfb_watch(obj)

        if not watch:
            return None

        competition = getattr(watch, "competition", None)
        return getattr(competition, "season", None) if competition else None

    def get_szfb_watch_id(self, obj):
        return self.get_szfb_team_watch_id(obj)

    def get_szfb_watch_label(self, obj):
        return self.get_szfb_team_watch_label(obj)

    def get_szfb_competition_name(self, obj):
        return self.get_szfb_team_watch_competition_name(obj)


class CategoryBirthYearsSerializer(serializers.ModelSerializer):
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    szfb_team_watch_id = serializers.SerializerMethodField()
    szfb_team_watch_label = serializers.SerializerMethodField()
    szfb_team_watch_competition_name = serializers.SerializerMethodField()
    szfb_team_watch_competition_season = serializers.SerializerMethodField()
    szfb_watch_id = serializers.SerializerMethodField()
    szfb_watch_label = serializers.SerializerMethodField()
    szfb_competition_name = serializers.SerializerMethodField()

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
            "szfb_team_watch_id",
            "szfb_team_watch_label",
            "szfb_team_watch_competition_name",
            "szfb_team_watch_competition_season",
            "szfb_watch_id",
            "szfb_watch_label",
            "szfb_competition_name",
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

    def get_szfb_team_watch_id(self, obj):
        watch = get_category_szfb_watch(obj)
        return watch.id if watch else None

    def get_szfb_team_watch_label(self, obj):
        watch = get_category_szfb_watch(obj)
        return getattr(watch, "label", None) if watch else None

    def get_szfb_team_watch_competition_name(self, obj):
        watch = get_category_szfb_watch(obj)

        if not watch:
            return None

        competition = getattr(watch, "competition", None)
        return getattr(competition, "name", None) if competition else None

    def get_szfb_team_watch_competition_season(self, obj):
        watch = get_category_szfb_watch(obj)

        if not watch:
            return None

        competition = getattr(watch, "competition", None)
        return getattr(competition, "season", None) if competition else None

    def get_szfb_watch_id(self, obj):
        return self.get_szfb_team_watch_id(obj)

    def get_szfb_watch_label(self, obj):
        return self.get_szfb_team_watch_label(obj)

    def get_szfb_competition_name(self, obj):
        return self.get_szfb_team_watch_competition_name(obj)


class ClubSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSeason
        fields = [
            "id",
            "club",
            "season",
        ]