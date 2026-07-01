from django.urls import path

from .views import public_contact_detail, public_documents_list, public_links_list

urlpatterns = [
    path("contact/<slug:club_slug>/", public_contact_detail, name="public-contact-detail"),
    path("documents/<slug:club_slug>/", public_documents_list, name="public-documents-list"),
    path("links/<slug:club_slug>/", public_links_list, name="public-links-list"),
]