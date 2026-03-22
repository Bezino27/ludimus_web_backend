from rest_framework import serializers
from .models import Match


class MatchSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "opponent",
            "competition",
            "round_label",
            "match_date",
            "location",
            "is_home",
            "home_score",
            "away_score",
            "summary",
            "is_published",
            "team_name",
            "club_slug",
        ]