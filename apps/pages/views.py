from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Page
from .serializers import PageSerializer


class ClubPageDetailView(generics.RetrieveAPIView):
    serializer_class = PageSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]
        return (
            Page.objects.filter(
                club__slug=club_slug,
                club__is_active=True,
                is_published=True,
            )
            .select_related("club")
            .prefetch_related("sections")
        )


class ClubPageHomeView(generics.RetrieveAPIView):
    serializer_class = PageSerializer

    def get_object(self):
        club_slug = self.kwargs["club_slug"]
        return (
            Page.objects.filter(
                club__slug=club_slug,
                club__is_active=True,
                is_published=True,
                is_homepage=True,
            )
            .select_related("club")
            .prefetch_related("sections")
            .get()
        )


class ClubPageNavigationView(APIView):
    def get(self, request, club_slug):
        pages = Page.objects.filter(
            club__slug=club_slug,
            club__is_active=True,
            is_published=True,
        ).order_by("navigation_order", "title")

        def map_page(page):
            return {
                "id": page.id,
                "title": page.title,
                "menu_title": page.menu_title,
                "slug": page.slug,
                "page_type": page.page_type,
                "navigation_order": page.navigation_order,
            }

        header_pages = [map_page(page) for page in pages if page.show_in_header]
        footer_pages = [map_page(page) for page in pages if page.show_in_footer]

        return Response({
            "header_pages": header_pages,
            "footer_pages": footer_pages,
        })