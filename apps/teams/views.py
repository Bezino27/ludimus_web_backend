from rest_framework import generics
from .models import Category, ClubSeason
from .serializers import (
    CategorySerializer,
    CategoryBirthYearsSerializer,
    ClubSeasonSerializer,
)

class ClubCategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
            is_active=True,
        ).select_related("club").order_by("order", "name")


class CategoryBirthYearsDetailView(generics.RetrieveAPIView):
    serializer_class = CategoryBirthYearsSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Category.objects.filter(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
            is_active=True,
        ).select_related("club")
class ClubSeasonDetailView(generics.RetrieveAPIView):
    serializer_class = ClubSeasonSerializer

    def get_object(self):
        return ClubSeason.objects.select_related("club").get(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
        )
