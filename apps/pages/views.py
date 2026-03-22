from rest_framework import generics
from .models import Page
from .serializers import PageSerializer


class ClubPageDetailView(generics.RetrieveAPIView):
    serializer_class = PageSerializer
    lookup_field = "slug"

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]
        return Page.objects.filter(
            club__slug=club_slug,
            club__is_active=True,
            is_published=True,
        ).select_related("club")