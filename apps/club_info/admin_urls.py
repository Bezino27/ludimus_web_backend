from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .admin_views import (
    AdminClubDocumentViewSet,
    AdminClubLinkViewSet,
    admin_contact_detail,
    club_info_overview,
)

router = DefaultRouter()
router.register("documents", AdminClubDocumentViewSet, basename="admin-club-documents")
router.register("links", AdminClubLinkViewSet, basename="admin-club-links")

urlpatterns = [
    path("overview/", club_info_overview, name="admin-club-info-overview"),
    path("contact/", admin_contact_detail, name="admin-club-info-contact"),
    path("", include(router.urls)),
]