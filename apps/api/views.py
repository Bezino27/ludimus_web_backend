from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.clubs.models import Club
from apps.clubs.serializers import ClubSerializer
from apps.homepage.models import HomepageSection
from apps.homepage.serializers import HomepageSectionSerializer
from apps.posts.models import Post
from apps.posts.serializers import PostListSerializer
from apps.matches.models import Match
from apps.matches.serializers import MatchSerializer
from apps.partners.models import Partner
from apps.partners.serializers import PartnerSerializer
from apps.pages.models import Page
from apps.pages.serializers import PageSerializer


class PublicHomeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, club_slug):
        club = Club.objects.filter(slug=club_slug, is_active=True).first()

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

        matches = (
            Match.objects.filter(
                club=club,
                is_published=True,
            )
            .select_related("team", "club")
            .order_by("-match_date")[:8]
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
            "matches": MatchSerializer(matches, many=True, context={"request": request}).data,
            "partners": PartnerSerializer(partners, many=True, context={"request": request}).data,
            "menu_pages": PageSerializer(menu_pages, many=True, context={"request": request}).data,
        }

        return Response(data)