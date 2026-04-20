from django.urls import path
from .views import (
    ClubCategoryListView,
    CategoryBirthYearsDetailView,
    ClubSeasonDetailView,
)

urlpatterns = [
    path("<slug:club_slug>/season/", ClubSeasonDetailView.as_view(), name="club-season-detail"),
    path("<slug:club_slug>/", ClubCategoryListView.as_view(), name="club-category-list"),
    path(
        "<slug:club_slug>/<slug:slug>/",
        CategoryBirthYearsDetailView.as_view(),
        name="category-birth-years-detail",
    ),
]