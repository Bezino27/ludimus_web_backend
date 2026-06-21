from rest_framework import generics
from django.db.models import Prefetch
from apps.club_info.models import ClubLink
from .models import Club
from .serializers import ClubSerializer


class ClubDetailBySlugView(generics.RetrieveAPIView):
    queryset = Club.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            "links",
            queryset=ClubLink.objects.filter(is_active=True).order_by("order", "title"),
        )
    )
    serializer_class = ClubSerializer
    lookup_field = "slug"
