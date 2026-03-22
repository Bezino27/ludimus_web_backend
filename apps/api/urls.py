from django.urls import path
from .views import PublicHomeView

urlpatterns = [
    path("home/<slug:club_slug>/", PublicHomeView.as_view(), name="public-home"),
]