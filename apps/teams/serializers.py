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
    """
    Dočasné bezpečné prepojenie Category -> SzfbTeamWatch.

    V modeli Category zatiaľ nie je priame FK na SzfbTeamWatch.
    Preto nájdeme aktívny watch podľa labelu/názvu, napr.:
    Category: Juniori
    SzfbTeamWatch label: ATU Košice - Juniori

    Keď neskôr doplníme priame FK pole, túto logiku nahradíme čistým prepojením.
    """
    try:
        from apps.scraper.models import SzfbTeamWatch
    except Exception:
        return None

    category_name = normalize_text(category.name)
    category_slug = normalize_text(category.slug)
    club_name = normalize_text(getattr(category.club, "name", ""))

    queryset = SzfbTeamWatch.objects.filter(is_active=True).select_related("competition")

    field_names = {field.name for field in SzfbTeamWatch._meta.get_fields()}

    if "club" in field_names:
        queryset = queryset.filter(club=category.club)

    watches = list(queryset.order_by("id"))

    def score_watch(watch):
        label = normalize_text(getattr(watch, "label", ""))
        team_name = normalize_text(getattr(watch, "team_name", ""))
        competition_name = normalize_text(getattr(getattr(watch, "competition", None), "name", ""))

        haystack = " ".join([label, team_name, competition_name]).strip()

        score = 0

        if club_name and club_name in haystack:
            score += 10

        if category_name and category_name in haystack:
            score += 100

        if category_slug and category_slug in haystack:
            score += 80

        return score

    scored_watches = [
        (score_watch(watch), watch)
        for watch in watches
    ]

    scored_watches = [
        item for item in scored_watches
        if item[0] > 0
    ]

    if not scored_watches:
        return None

    scored_watches.sort(key=lambda item: item[0], reverse=True)
    return scored_watches[0][1]


class CategorySerializer(serializers.ModelSerializer):
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
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

    def get_szfb_watch_id(self, obj):
        watch = get_category_szfb_watch(obj)
        return watch.id if watch else None

    def get_szfb_watch_label(self, obj):
        watch = get_category_szfb_watch(obj)
        return getattr(watch, "label", None) if watch else None

    def get_szfb_competition_name(self, obj):
        watch = get_category_szfb_watch(obj)

        if not watch:
            return None

        competition = getattr(watch, "competition", None)
        return getattr(competition, "name", None) if competition else None


class CategoryBirthYearsSerializer(serializers.ModelSerializer):
    display_years = serializers.SerializerMethodField()
    hero_image_url = serializers.SerializerMethodField()
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

    def get_szfb_watch_id(self, obj):
        watch = get_category_szfb_watch(obj)
        return watch.id if watch else None

    def get_szfb_watch_label(self, obj):
        watch = get_category_szfb_watch(obj)
        return getattr(watch, "label", None) if watch else None

    def get_szfb_competition_name(self, obj):
        watch = get_category_szfb_watch(obj)

        if not watch:
            return None

        competition = getattr(watch, "competition", None)
        return getattr(competition, "name", None) if competition else None


class ClubSeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubSeason
        fields = [
            "id",
            "club",
            "season",
        ]