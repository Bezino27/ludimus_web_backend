from django.urls import path
from .views import ClubTeamListView, ClubTeamMemberListView

urlpatterns = [
    path("<slug:club_slug>/", ClubTeamListView.as_view(), name="club-team-list"),
    path("<slug:club_slug>/members/", ClubTeamMemberListView.as_view(), name="club-team-member-list"),
]