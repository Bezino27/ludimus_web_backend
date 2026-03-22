from django.urls import path
from .views import ClubPostListView, ClubPostDetailView 

urlpatterns = [
    path("<slug:club_slug>/", ClubPostListView.as_view(), name="club-post-list"),
    path("<slug:club_slug>/<slug:slug>/", ClubPostDetailView.as_view(), name="club-post-detail"),
]