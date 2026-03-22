from rest_framework import generics
from .models import Match
from .serializers import MatchSerializer


class ClubMatchListView(generics.ListAPIView):
    serializer_class = MatchSerializer

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]
        return (
            Match.objects.filter(
                club__slug=club_slug,
                club__is_active=True,
                is_published=True,
            )
            .select_related("club", "team")
            .order_by("-match_date")
        )