from rest_framework import serializers
from apps.scraper.models import SzfbStandingRow, SzfbMatch, SzfbTeamWatch


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