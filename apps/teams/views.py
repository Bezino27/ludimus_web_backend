from rest_framework import generics
from .models import Team, TeamMember
from .serializers import TeamSerializer, TeamMemberSerializer


class ClubTeamListView(generics.ListAPIView):
    serializer_class = TeamSerializer

    def get_queryset(self):
        return Team.objects.filter(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
            is_active=True,
        ).order_by("name")


class ClubTeamMemberListView(generics.ListAPIView):
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        queryset = TeamMember.objects.filter(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
            is_active=True,
        ).select_related("team", "club")

        team_slug = self.request.query_params.get("team")
        role = self.request.query_params.get("role")

        if team_slug:
            queryset = queryset.filter(team__slug=team_slug)

        if role:
            queryset = queryset.filter(role=role)

        return queryset.order_by("order", "last_name", "first_name")