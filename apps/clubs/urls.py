from django.urls import path
from .views import ClubDetailBySlugView

urlpatterns = [
    path("<slug:slug>/", ClubDetailBySlugView.as_view(), name="club-detail"),
]