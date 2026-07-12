from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clubs.models import Club, ClubMembership
from apps.common.permissions import EDITOR_ROLES

from .admin_serializers import AdminCategorySerializer, AdminClubSeasonSerializer
from .models import Category, ClubSeason
from .utils import recalculate_categories_for_club


def get_editor_club_ids(user):
    return ClubMembership.objects.filter(
        user=user,
        is_active=True,
        role__in=EDITOR_ROLES,
    ).values_list("club_id", flat=True)


def get_editor_club_or_403(user, club_slug):
    club_ids = get_editor_club_ids(user)

    try:
        return Club.objects.get(
            id__in=club_ids,
            slug=club_slug,
            is_active=True,
        )
    except Club.DoesNotExist:
        raise PermissionDenied("Nemáš oprávnenie upravovať tento klub.")


class AdminCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        club_ids = get_editor_club_ids(self.request.user)

        queryset = Category.objects.filter(
            club_id__in=club_ids,
        ).select_related("club", "szfb_team_watch", "szfb_team_watch__competition").order_by("club__name", "season", "order", "name")

        club_slug = self.request.query_params.get("club")
        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        season = self.request.query_params.get("season")
        if season:
            queryset = queryset.filter(season=season)

        is_active = self.request.query_params.get("is_active")
        if is_active in ["true", "1"]:
            queryset = queryset.filter(is_active=True)
        elif is_active in ["false", "0"]:
            queryset = queryset.filter(is_active=False)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data.get("club")

        if not club:
            raise ValidationError({"club": "Klub je povinný."})

        allowed_club_ids = list(get_editor_club_ids(self.request.user))

        if club.id not in allowed_club_ids:
            raise PermissionDenied("Nemáš oprávnenie vytvárať kategórie pre tento klub.")

        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        club = serializer.validated_data.get("club", instance.club)

        allowed_club_ids = list(get_editor_club_ids(self.request.user))

        if club.id not in allowed_club_ids:
            raise PermissionDenied("Nemáš oprávnenie upravovať túto kategóriu.")

        serializer.save()

    @action(detail=False, methods=["get"], url_path="season-options")
    def season_options(self, request):
        club_slug = request.query_params.get("club")

        if not club_slug:
            raise ValidationError({"club": "Query parameter club je povinný."})

        club = get_editor_club_or_403(request.user, club_slug)

        seasons = set(
            Category.objects.filter(club=club)
            .exclude(season="")
            .values_list("season", flat=True)
            .distinct()
        )

        current_season = getattr(club, "current_season", None)
        if current_season and current_season.season:
            seasons.add(current_season.season)

        return Response(
            {
                "club": club.id,
                "club_slug": club.slug,
                "seasons": sorted(seasons, reverse=True),
            }
        )


class AdminClubSeasonViewSet(viewsets.ModelViewSet):
    serializer_class = AdminClubSeasonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        club_ids = get_editor_club_ids(self.request.user)

        queryset = ClubSeason.objects.filter(
            club_id__in=club_ids,
        ).select_related("club").order_by("club__name")

        club_slug = self.request.query_params.get("club")
        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data.get("club")

        if not club:
            raise ValidationError({"club": "Klub je povinný."})

        allowed_club_ids = list(get_editor_club_ids(self.request.user))

        if club.id not in allowed_club_ids:
            raise PermissionDenied("Nemáš oprávnenie nastaviť sezónu pre tento klub.")

        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        old_season = instance.season

        recalculate_categories = serializer.validated_data.get(
            "recalculate_categories",
            True,
        )

        updated_instance = serializer.save()

        if recalculate_categories and old_season != updated_instance.season:
            recalculate_categories_for_club(
                updated_instance.club,
                updated_instance.season,
            )

    @action(detail=False, methods=["get", "patch"], url_path="current")
    def current(self, request):
        club_slug = request.query_params.get("club")

        if not club_slug:
            raise ValidationError({"club": "Query parameter club je povinný."})

        club = get_editor_club_or_403(request.user, club_slug)

        club_season, _created = ClubSeason.objects.get_or_create(
            club=club,
            defaults={"season": "2025/2026"},
        )

        if request.method == "GET":
            serializer = self.get_serializer(club_season)
            return Response(serializer.data)

        old_season = club_season.season

        serializer = self.get_serializer(
            club_season,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        recalculate_categories = serializer.validated_data.get(
            "recalculate_categories",
            True,
        )

        updated_instance = serializer.save()

        if recalculate_categories and old_season != updated_instance.season:
            recalculate_categories_for_club(
                updated_instance.club,
                updated_instance.season,
            )

        return Response(
            self.get_serializer(updated_instance).data,
            status=status.HTTP_200_OK,
        )