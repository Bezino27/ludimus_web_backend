from rest_framework import generics
from .models import HomepageSection
from .serializers import HomepageSectionSerializer


class ClubHomepageSectionListView(generics.ListAPIView):
    serializer_class = HomepageSectionSerializer

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]
        return HomepageSection.objects.filter(
            club__slug=club_slug,
            club__is_active=True,
            is_active=True,
        ).order_by("order", "id")
