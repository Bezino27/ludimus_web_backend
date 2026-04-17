from rest_framework import generics
from .models import Category
from .serializers import CategorySerializer, CategoryBirthYearsSerializer


class ClubCategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
            is_active=True,
        ).order_by("order", "name")


class CategoryBirthYearsDetailView(generics.RetrieveAPIView):
    serializer_class = CategoryBirthYearsSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Category.objects.filter(
            club__slug=self.kwargs["club_slug"],
            club__is_active=True,
            is_active=True,
        )