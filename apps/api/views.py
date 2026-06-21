from django.db.models import Prefetch
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.clubs.models import Club
from apps.clubs.serializers import ClubSerializer
from apps.club_info.models import ClubLink
from apps.homepage.models import HomepageSection
from apps.homepage.serializers import HomepageSectionSerializer
from apps.posts.models import Post
from apps.posts.serializers import PostListSerializer
from apps.partners.models import Partner
from apps.partners.serializers import PartnerSerializer
from apps.pages.models import Page
from apps.pages.serializers import PageSerializer


class PublicHomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, club_slug):
        club = (
            Club.objects.filter(slug=club_slug, is_active=True)
            .prefetch_related(
                Prefetch(
                    "links",
                    queryset=ClubLink.objects.filter(is_active=True).order_by(
                        "order",
                        "title",
                    ),
                )
            )
            .first()
        )

        if not club:
            return Response({"detail": "Klub neexistuje."}, status=404)

        sections = HomepageSection.objects.filter(
            club=club,
            is_active=True,
        ).order_by("order", "id")

        latest_posts = (
            Post.objects.filter(
                club=club,
                status="published",
            )
            .select_related("category", "author", "club")
            .order_by("-published_at", "-created_at")[:6]
        )

        partners = Partner.objects.filter(
            club=club,
            is_active=True,
        ).order_by("order", "name")

        menu_pages = Page.objects.filter(
            club=club,
            is_published=True,
            show_in_menu=True,
        ).order_by("menu_order", "title")

        data = {
            "club": ClubSerializer(club, context={"request": request}).data,
            "sections": HomepageSectionSerializer(sections, many=True, context={"request": request}).data,
            "latest_posts": PostListSerializer(latest_posts, many=True, context={"request": request}).data,
            "partners": PartnerSerializer(partners, many=True, context={"request": request}).data,
            "menu_pages": PageSerializer(menu_pages, many=True, context={"request": request}).data,
        }

        return Response(data)
