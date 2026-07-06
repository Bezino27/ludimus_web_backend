from django.urls import path

from apps.club_info.admin_views import (
    AdminClubDocumentViewSet,
    AdminClubLinkViewSet,
    admin_contact_detail,
    club_info_overview,
)

document_list = AdminClubDocumentViewSet.as_view({
    "get": "list",
    "post": "create",
})
document_detail = AdminClubDocumentViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})
link_list = AdminClubLinkViewSet.as_view({
    "get": "list",
    "post": "create",
})
link_detail = AdminClubLinkViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path("overview/", club_info_overview, name="admin-club-info-overview"),
    path("contact/", admin_contact_detail, name="admin-club-info-contact"),
    path("documents/", document_list, name="admin-club-info-document-list"),
    path(
        "documents/<int:pk>/",
        document_detail,
        name="admin-club-info-document-detail",
    ),
    path("links/", link_list, name="admin-club-info-link-list"),
    path(
        "links/<int:pk>/",
        link_detail,
        name="admin-club-info-link-detail",
    ),
]
