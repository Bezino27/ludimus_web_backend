from rest_framework import serializers
from apps.common.image_uploads import optimize_uploaded_image
from apps.scraper.models import SzfbTeamWatch

from .models import (
    Category,
    CategoryLink,
    CategoryTraining,
    ClubSeason,
    TrainingLocation,
)
from .serializers import format_display_years, get_category_szfb_watch


class AdminTrainingLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingLocation
        fields = [
            "id", "club", "name", "address", "latitude", "longitude",
            "order", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AdminCategoryTrainingSerializer(serializers.ModelSerializer):
    day = serializers.CharField(source="get_weekday_display", read_only=True)
    time = serializers.SerializerMethodField()
    location_name = serializers.CharField(source="location.name", read_only=True)
    location_address = serializers.CharField(source="location.address", read_only=True)
    latitude = serializers.FloatField(source="location.latitude", read_only=True)
    longitude = serializers.FloatField(source="location.longitude", read_only=True)

    class Meta:
        model = CategoryTraining
        fields = [
            "id", "category", "location", "location_name", "location_address",
            "latitude", "longitude", "weekday", "day", "start_time", "time",
            "order", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "location_name", "location_address", "latitude", "longitude",
            "day", "time", "created_at", "updated_at",
        ]

    def get_time(self, obj):
        return obj.start_time.strftime("%H:%M")

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", None))
        location = attrs.get("location", getattr(self.instance, "location", None))

        if category and location and category.club_id != location.club_id:
            raise serializers.ValidationError(
                {"location": "Tréningové miesto musí patriť rovnakému klubu ako kategória."}
            )
        return attrs


class AdminCategoryLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryLink
        fields = [
            "id", "category", "title", "description", "cta_text", "url",
            "order", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "url": {"required": False, "allow_blank": True},
            "description": {"required": False, "allow_blank": True},
            "cta_text": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        category = attrs.get("category", getattr(self.instance, "category", None))
        title = attrs.get("title", getattr(self.instance, "title", ""))
        if category and title:
            duplicate = CategoryLink.objects.filter(
                category=category,
                title__iexact=title.strip(),
            )

            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)

            if duplicate.exists():
                raise serializers.ValidationError(
                    {"title": "Odkaz s týmto názvom už v kategórii existuje."}
                )

        return attrs


class AdminCategorySerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
    szfb_team_watch = serializers.PrimaryKeyRelatedField(
        queryset=SzfbTeamWatch.objects.select_related("club", "competition"),
        required=False,
        allow_null=True,
    )
    szfb_team_watch_id = serializers.SerializerMethodField()
    szfb_team_watch_label = serializers.SerializerMethodField()
    szfb_team_watch_competition_name = serializers.SerializerMethodField()
    szfb_team_watch_competition_season = serializers.SerializerMethodField()
    szfb_watch_id = serializers.SerializerMethodField()
    szfb_watch_label = serializers.SerializerMethodField()
    szfb_competition_name = serializers.SerializerMethodField()
    trainings = AdminCategoryTrainingSerializer(many=True, read_only=True)
    links = AdminCategoryLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            "id", "club", "club_name", "name", "slug", "season",
            "birth_year_from", "birth_year_to", "display_years", "category_subname",
            "league_name", "hero_image", "hero_image_url", "coach_name", "coach_email",
            "coach_phone", "order", "is_active", "szfb_team_watch",
            "szfb_team_watch_id", "szfb_team_watch_label",
            "szfb_team_watch_competition_name", "szfb_team_watch_competition_season",
            "szfb_watch_id", "szfb_watch_label", "szfb_competition_name",
            "trainings", "links", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "club_name", "display_years", "hero_image_url",
            "szfb_team_watch_id", "szfb_team_watch_label",
            "szfb_team_watch_competition_name", "szfb_team_watch_competition_season",
            "szfb_watch_id", "szfb_watch_label", "szfb_competition_name",
            "trainings", "links", "created_at", "updated_at",
        ]

    def get_display_years(self, obj):
        return format_display_years(obj)

    def get_hero_image_url(self, obj):
        request = self.context.get("request")
        if obj.hero_image:
            return request.build_absolute_uri(obj.hero_image.url) if request else obj.hero_image.url
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

    def validate_hero_image(self, hero_image):
        return optimize_uploaded_image(hero_image, "hero", filename_prefix="category-hero")

    def validate(self, attrs):
        birth_year_from = attrs.get("birth_year_from", getattr(self.instance, "birth_year_from", None))
        birth_year_to = attrs.get("birth_year_to", getattr(self.instance, "birth_year_to", None))

        if birth_year_from is not None and birth_year_to is not None:
            if birth_year_from <= 1900 or birth_year_to <= 1900:
                raise serializers.ValidationError("Roky narodenia musia byť väčšie ako 1900.")
            if birth_year_from > 2100 or birth_year_to > 2100:
                raise serializers.ValidationError("Roky narodenia sú príliš vysoké.")

        instance = getattr(self, "instance", None)
        club = attrs.get("club", getattr(instance, "club", None))
        season = attrs.get("season", getattr(instance, "season", ""))
        watch = attrs.get("szfb_team_watch", getattr(instance, "szfb_team_watch", None))

        if watch:
            if not club:
                raise serializers.ValidationError({"club": "Klub je povinný."})
            if watch.club_id and watch.club_id != club.id:
                raise serializers.ValidationError({"szfb_team_watch": "SZFB sledovanie musí patriť rovnakému klubu."})
            competition = getattr(watch, "competition", None)
            watch_season = getattr(competition, "season", "") if competition else ""
            if season and watch_season and season != watch_season:
                raise serializers.ValidationError({"szfb_team_watch": f"SZFB sledovanie je z inej sezóny ({watch_season})."})

        return attrs


class AdminClubSeasonSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)
    available_seasons = serializers.SerializerMethodField()
    recalculate_categories = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = ClubSeason
        fields = [
            "id", "club", "club_name", "club_slug", "season", "available_seasons",
            "recalculate_categories", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "club_name", "club_slug", "available_seasons", "created_at", "updated_at",
        ]

    def get_available_seasons(self, obj):
        seasons = {obj.season} if obj.season else set()
        seasons.update(
            Category.objects.filter(club=obj.club)
            .exclude(season="")
            .values_list("season", flat=True)
            .distinct()
        )
        return sorted(seasons, reverse=True)

    def update(self, instance, validated_data):
        validated_data.pop("recalculate_categories", None)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data.pop("recalculate_categories", None)
        return super().create(validated_data)
