from django.urls import path
from .views import ClubHomepageSectionListView

urlpatterns = [
    path("<slug:club_slug>/", ClubHomepageSectionListView.as_view(), name="club-homepage-sections"),
]