from django.urls import path
from .views import ClubPageDetailView

urlpatterns = [
    path("<slug:club_slug>/<slug:slug>/", ClubPageDetailView.as_view(), name="club-page-detail"),
]