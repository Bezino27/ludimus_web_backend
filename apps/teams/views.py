from django.db.models import Prefetch
from rest_framework import generics

from .models import Category, CategoryLink, CategoryTraining, ClubSeason
from .serializers import (
    CategoryBirthYearsSerializer,
    CategorySerializer,
    ClubSeasonSerializer,
)


class CategoryQuerysetMixin:
    def get_base_queryset(self):
        return Category.objects.filter(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
            is_active=True,
        ).select_related(
            "club",
            "szfb_team_watch",
            "szfb_team_watch__competition",
        ).prefetch_related(
            Prefetch(
                "trainings",
                queryset=CategoryTraining.objects.filter(is_active=True)
                .select_related("location")
                .filter(location__is_active=True)
                .order_by("order", "weekday", "start_time"),
            ),
            Prefetch(
                "links",
                queryset=CategoryLink.objects.filter(is_active=True)
                .exclude(url="")
                .order_by("order", "title"),
            ),
        )


class ClubCategoryListView(CategoryQuerysetMixin, generics.ListAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return self.get_base_queryset().order_by("order", "name")


class CategoryBirthYearsDetailView(CategoryQuerysetMixin, generics.RetrieveAPIView):
    serializer_class = CategoryBirthYearsSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return self.get_base_queryset()


class ClubSeasonDetailView(generics.RetrieveAPIView):
    serializer_class = ClubSeasonSerializer

    def get_object(self):
        return ClubSeason.objects.select_related("club").get(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
        )
