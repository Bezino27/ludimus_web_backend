from django.urls import path
from .views import ClubCategoryListView, CategoryBirthYearsDetailView

urlpatterns = [
    path("<slug:club_slug>/", ClubCategoryListView.as_view(), name="club-category-list"),
    path(
        "<slug:club_slug>/<slug:slug>/",
        CategoryBirthYearsDetailView.as_view(),
        name="category-birth-years-detail",
    ),
]