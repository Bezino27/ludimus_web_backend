from rest_framework import serializers

from .models import (
    Category,
    CategoryLink,
    CategoryTraining,
    ClubSeason,
    TrainingLocation,
)


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


def get_category_szfb_watch(category):
    return getattr(category, "szfb_team_watch", None)


class PublicTrainingLocationSerializer(serializers.ModelSerializer):
    lat = serializers.FloatField(source="latitude")
    lng = serializers.FloatField(source="longitude")

    class Meta:
        model = TrainingLocation
        fields = ["id", "name", "address", "lat", "lng"]


class PublicCategoryTrainingSerializer(serializers.ModelSerializer):
    day = serializers.CharField(source="get_weekday_display")
    time = serializers.SerializerMethodField()
    location = PublicTrainingLocationSerializer(read_only=True)

    class Meta:
        model = CategoryTraining
        fields = ["id", "day", "time", "location", "order"]

    def get_time(self, obj):
        return obj.start_time.strftime("%H:%M")


class PublicCategoryLinkSerializer(serializers.ModelSerializer):
    cta = serializers.CharField(source="cta_text")
    href = serializers.URLField(source="url")

    class Meta:
        model = CategoryLink
        fields = ["id", "title", "description", "cta", "href", "order"]


class CategoryBaseSerializer(serializers.ModelSerializer):
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    szfb_team_watch_id = serializers.SerializerMethodField()
    szfb_team_watch_label = serializers.SerializerMethodField()
    szfb_team_watch_competition_name = serializers.SerializerMethodField()
    szfb_team_watch_competition_season = serializers.SerializerMethodField()
    szfb_watch_id = serializers.SerializerMethodField()
    szfb_watch_label = serializers.SerializerMethodField()
    szfb_competition_name = serializers.SerializerMethodField()
    trainings = PublicCategoryTrainingSerializer(many=True, read_only=True)
    links = PublicCategoryLinkSerializer(many=True, read_only=True)

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
        competition = getattr(watch, "competition", None) if watch else None
        return getattr(competition, "name", None) if competition else None

    def get_szfb_team_watch_competition_season(self, obj):
        watch = get_category_szfb_watch(obj)
        competition = getattr(watch, "competition", None) if watch else None
        return getattr(competition, "season", None) if competition else None

    def get_szfb_watch_id(self, obj):
        return self.get_szfb_team_watch_id(obj)

    def get_szfb_watch_label(self, obj):
        return self.get_szfb_team_watch_label(obj)

    def get_szfb_competition_name(self, obj):
        return self.get_szfb_team_watch_competition_name(obj)


class CategorySerializer(CategoryBaseSerializer):
    class Meta:
        model = Category
        fields = [
            "id", "club", "name", "slug", "season", "birth_year_from",
            "birth_year_to", "category_subname", "display_years", "league_name",
            "hero_image_url", "order", "is_active", "coach_name", "coach_email",
            "coach_phone", "szfb_team_watch_id", "szfb_team_watch_label",
            "szfb_team_watch_competition_name", "szfb_team_watch_competition_season",
            "szfb_watch_id", "szfb_watch_label", "szfb_competition_name",
            "trainings", "links",
        ]


class CategoryBirthYearsSerializer(CategoryBaseSerializer):
    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "season", "birth_year_from", "birth_year_to",
            "category_subname", "display_years", "league_name", "hero_image_url",
            "coach_name", "coach_email", "coach_phone", "szfb_team_watch_id",
            "szfb_team_watch_label", "szfb_team_watch_competition_name",
            "szfb_team_watch_competition_season", "szfb_watch_id", "szfb_watch_label",
            "szfb_competition_name", "trainings", "links",
        ]


class ClubSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSeason
        fields = ["id", "club", "season"]
