from rest_framework import serializers
from django.contrib.auth.models import User

from apps.clubs.models import ClubMembership


class ClubMembershipSerializer(serializers.ModelSerializer):
    club_id = serializers.IntegerField(source="club.id", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True)
    club_slug = serializers.CharField(source="club.slug", read_only=True)

    class Meta:
        model = ClubMembership
        fields = [
            "id",
            "club_id",
            "club_name",
            "club_slug",
            "role",
            "is_active",
        ]


class MeSerializer(serializers.ModelSerializer):
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "memberships",
        ]

    def get_memberships(self, obj):
        memberships = obj.club_memberships.filter(is_active=True).select_related("club")
        return ClubMembershipSerializer(memberships, many=True).data