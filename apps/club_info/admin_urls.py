from django.urls import path

from apps.scraper.views import (
    AdminSzfbCompetitionListView,
    AdminSzfbCompetitionSyncView,
    AdminSzfbTeamWatchListView,
)

urlpatterns = [
    path(
        "watches/",
        AdminSzfbTeamWatchListView.as_view(),
        name="admin-szfb-watch-list",
    ),
    path(
        "competitions/",
        AdminSzfbCompetitionListView.as_view(),
        name="admin-szfb-competition-list",
    ),
    path(
        "competitions/<int:competition_id>/sync/",
        AdminSzfbCompetitionSyncView.as_view(),
        name="admin-szfb-competition-sync",
    ),
]