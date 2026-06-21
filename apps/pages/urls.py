from django.urls import path

from .views import ClubPageDetailView, ClubPageHomeView, ClubPageNavigationView

urlpatterns = [
    path("<slug:club_slug>/navigation/", ClubPageNavigationView.as_view(), name="club-page-navigation"),
    path("<slug:club_slug>/home/", ClubPageHomeView.as_view(), name="club-page-home"),
    path("<slug:club_slug>/by-slug/<slug:slug>/", ClubPageDetailView.as_view(), name="club-page-detail"),
]