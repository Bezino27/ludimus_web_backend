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
            .prefetch_related("sections", "sections__items")
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
            .prefetch_related("sections", "sections__items")
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
                "menu_group": page.menu_group,
                "menu_group_title": page.menu_group_title,
                "url": page.get_public_path(),
            }

        main_pages = [
            map_page(page)
            for page in pages
            if page.menu_group == "main"
            or (page.show_in_header and page.menu_group == "hidden")
        ]
        youth_pages = [map_page(page) for page in pages if page.menu_group == "youth"]
        cta_page = next((map_page(page) for page in pages if page.menu_group == "cta"), None)
        footer_pages = [
            map_page(page)
            for page in pages
            if page.show_in_footer or page.menu_group == "footer"
        ]

        dropdowns = []

        if youth_pages:
            dropdowns.append({
                "title": youth_pages[0].get("menu_group_title") or "Mládež",
                "group": "youth",
                "items": youth_pages,
            })

        return Response({
            "main": main_pages,
            "dropdowns": dropdowns,
            "cta": cta_page,
            "footer": footer_pages,
            "header": main_pages,
            "header_pages": main_pages,
            "footer_pages": footer_pages,
        })
