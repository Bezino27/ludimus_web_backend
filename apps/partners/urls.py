from django.urls import path
from .views import ClubPartnerListView

urlpatterns = [
    path("<slug:club_slug>/", ClubPartnerListView.as_view(), name="club-partner-list"),
]