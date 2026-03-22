from django.urls import path
from .views import ClubMatchListView

urlpatterns = [
    path("<slug:club_slug>/", ClubMatchListView.as_view(), name="club-match-list"),
]