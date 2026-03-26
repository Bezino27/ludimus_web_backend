from django.urls import path
from apps.scraper.views import (
    SzfbTeamWatchDetailView,
    SzfbWatchDashboardView,
    SzfbWatchResultsView,
    SzfbWatchStandingsView,
    SzfbWatchUpcomingView,
    SzfbWatchNextMatchView,
)

urlpatterns = [
    path("watch/<int:pk>/", SzfbTeamWatchDetailView.as_view(), name="szfb-watch-detail"),
    path("watch/<int:watch_id>/dashboard/", SzfbWatchDashboardView.as_view(), name="szfb-watch-dashboard"),
    path("watch/<int:watch_id>/standings/", SzfbWatchStandingsView.as_view(), name="szfb-watch-standings"),
    path("watch/<int:watch_id>/results/", SzfbWatchResultsView.as_view(), name="szfb-watch-results"),
    path("watch/<int:watch_id>/upcoming/", SzfbWatchUpcomingView.as_view(), name="szfb-watch-upcoming"),
    path("watch/<int:watch_id>/next-match/", SzfbWatchNextMatchView.as_view(), name="szfb-watch-next-match"),

]