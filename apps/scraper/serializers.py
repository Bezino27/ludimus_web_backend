from rest_framework import serializers
from apps.scraper.models import SzfbStandingRow, SzfbMatch, SzfbTeamWatch, SzfbPlayerStat
from apps.scraper.services.szfb_scraper import format_player_name


class SzfbStandingRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = SzfbStandingRow
        fields = ["position", "team_name", "played", "points"]


class SzfbMatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SzfbMatch
        fields = ["id", "match_type", "match_date", "match_time", "opponent", "venue", "result", "is_home"]


class SzfbTeamWatchSerializer(serializers.ModelSerializer):
    competition_name = serializers.CharField(source="competition.name", read_only=True)
    competition_season = serializers.CharField(source="competition.season", read_only=True)

    class Meta:
        model = SzfbTeamWatch
        fields = ["id", "label", "team_name", "competition_name", "competition_season"]

class SzfbPlayerStatSerializer(serializers.ModelSerializer):
    player_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    display_position = serializers.SerializerMethodField()

    def get_player_name(self, obj):
        return format_player_name(obj.player_name)

    def get_photo_url(self, obj):
        if not obj.photo:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(obj.photo.url)

        return obj.photo.url

    def get_display_position(self, obj):
        return obj.player_position

    class Meta:
        model = SzfbPlayerStat
        fields = [
            "id",
            "rank",
            "player_name",
            "birth_year",
            "team_short_name",
            "player_position",
            "games",
            "goals",
            "assists",
            "points",
            "points_avg",
            "esp",
            "ppp",
            "shp",
            "pim",

            # Klubové údaje
            "photo",
            "photo_url",
            "jersey_number",
            "display_position",
            "bio",
            "is_active",
            "is_featured",
            "display_order",
        ]
