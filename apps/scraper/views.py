from threading import Thread
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scraper.models import (
    ClubPlayer,
    SzfbCompetition,
    SzfbGoalieStat,
    SzfbMatch,
    SzfbPlayerStat,
    SzfbWatchAutoSyncConfig,
    SzfbStandingRow,
    SzfbStandingZone,
    SzfbTeamBrand,
    SzfbTeamWatch,
)
from apps.scraper.serializers import (
    AdminClubPlayerSerializer,
    AdminClubPlayerUpdateSerializer,
    AdminSzfbCompetitionSerializer,
    AdminSzfbGoalieStatSerializer,
    AdminSzfbMatchSerializer,
    AdminSzfbPlayerStatSerializer,
    AdminSzfbWatchAutoSyncConfigSerializer,
    AdminSzfbPlayerStatUpdateSerializer,
    AdminSzfbStandingRowSerializer,
    SzfbStandingZoneSerializer,
    AdminSzfbTeamBrandWriteSerializer,
    AdminSzfbWatchSettingsSerializer,
    SzfbMatchSerializer,
    SzfbMatchHistorySerializer,
    SzfbPlayerStatSerializer,
    SzfbStandingRowSerializer,
    SzfbTeamBrandSerializer,
    SzfbTeamWatchAdminSerializer,
    SzfbTeamWatchSerializer,
)
from apps.scraper.services.szfb_sync_runner import (
    can_start_competition_sync,
    expire_stale_running_competition_syncs,
    run_competition_sync,
)
from apps.scraper.services.szfb_match_history import (
    get_match_history_for_watch,
    get_recent_form_for_watch,
)
from apps.scraper.services.team_branding import (
    delete_team_brand_logo_if_unreferenced,
    get_club_team_brands,
)
from apps.common.revalidation import schedule_revalidation
from apps.scraper.revalidation import (
    get_player_revalidation_paths,
    get_player_stat_revalidation_paths,
    get_watch_revalidation_paths,
)
from apps.clubs.models import ClubMembership
from apps.common.permissions import EDITOR_ROLES


def get_editor_watch_or_404(request, watch_id):
    club_ids = ClubMembership.objects.filter(
        user=request.user,
        is_active=True,
        role__in=EDITOR_ROLES,
    ).values_list("club_id", flat=True)
    queryset = SzfbTeamWatch.objects.select_related("competition", "club").filter(
        club_id__in=club_ids
    )
    club_slug = request.data.get("club_slug") or request.query_params.get("club", "")
    if club_slug:
        queryset = queryset.filter(club__slug=club_slug)
    return get_object_or_404(queryset, id=watch_id)


def get_editor_club_or_404(request, club_slug):
    if not club_slug:
        raise ValidationError({"club": "Chýba identifikátor klubu."})

    membership = get_object_or_404(
        ClubMembership.objects.select_related("club"),
        user=request.user,
        is_active=True,
        role__in=EDITOR_ROLES,
        club__slug=club_slug,
    )
    return membership.club


def schedule_team_brand_revalidation(club, reason):
    paths = []
    watches = SzfbTeamWatch.objects.select_related("club", "competition").filter(
        club=club
    )
    for watch in watches:
        paths.extend(get_watch_revalidation_paths(watch))

    schedule_revalidation(
        list(dict.fromkeys(paths)),
        reason=reason,
        club_slug=club.slug,
    )


def schedule_competition_revalidation(competition, club, reason):
    paths = []
    watches = SzfbTeamWatch.objects.select_related("club", "competition").filter(
        competition=competition,
        club=club,
    )
    for watch in watches:
        paths.extend(get_watch_revalidation_paths(watch))

    schedule_revalidation(
        list(dict.fromkeys(paths)),
        reason=reason,
        club_slug=club.slug,
    )


class WatchBrandContextMixin:
    _watch_for_branding = None

    def get_branding_watch(self):
        if self._watch_for_branding is None:
            watch_id = self.kwargs.get("watch_id") or self.kwargs.get("pk")
            self._watch_for_branding = get_object_or_404(
                SzfbTeamWatch.objects.select_related("competition", "club"),
                id=watch_id,
            )
        return self._watch_for_branding

    def get_serializer_context(self):
        context = super().get_serializer_context()
        watch = self.get_branding_watch()
        context["team_brands"] = get_club_team_brands(watch.club)
        return context


def get_upcoming_matches(watch):
    now = timezone.localtime()
    return (
        watch.matches.filter(match_type="upcoming")
        .filter(
            Q(match_date__gt=now.date())
            | Q(match_date=now.date(), match_time__isnull=True)
            | Q(match_date=now.date(), match_time__gte=now.time())
        )
        .order_by("match_date", "match_time", "id")
    )


class SzfbTeamWatchDetailView(WatchBrandContextMixin, RetrieveAPIView):
    serializer_class = SzfbTeamWatchSerializer

    def get_object(self):
        return self.get_branding_watch()


class SzfbWatchStandingsView(WatchBrandContextMixin, ListAPIView):
    serializer_class = SzfbStandingRowSerializer

    def get_queryset(self):
        watch = self.get_branding_watch()
        return watch.competition.standings.order_by("position")


class SzfbWatchStandingZonesView(ListAPIView):
    serializer_class = SzfbStandingZoneSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]
        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition"),
            id=watch_id,
        )
        return watch.competition.standing_zones.filter(is_active=True).order_by(
            "display_order",
            "start_position",
            "id",
        )


class SzfbWatchResultsView(WatchBrandContextMixin, ListAPIView):
    serializer_class = SzfbMatchSerializer

    def get_queryset(self):
        watch = self.get_branding_watch()
        return (
            watch.matches
            .filter(match_type="finished")
            .order_by("-match_date", "-match_time")
        )


class SzfbWatchUpcomingView(WatchBrandContextMixin, ListAPIView):
    serializer_class = SzfbMatchSerializer

    def get_queryset(self):
        watch = self.get_branding_watch()
        return (
            watch.matches
            .filter(match_type="upcoming")
            .order_by("match_date", "match_time")
        )


class SzfbWatchDashboardView(APIView):
    def get(self, request, watch_id):
        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition", "club"),
            id=watch_id,
        )
        team_brands = get_club_team_brands(watch.club)
        serializer_context = {
            "request": request,
            "team_brands": team_brands,
        }

        standings = watch.competition.standings.order_by("position")
        standing_zones = watch.competition.standing_zones.filter(
            is_active=True
        ).order_by("display_order", "start_position", "id")
        results = get_match_history_for_watch(watch)[:5]
        upcoming = get_upcoming_matches(watch)[:8]

        player_stats = (
            watch.player_stats
            .select_related("club_player")
            .filter(
                Q(club_player__is_active=True)
                | Q(club_player__isnull=True, is_active=True)
            )
            .order_by("-points", "-goals", "-assists", "-games", "player_name")[:8]
        )

        return Response(
            {
                "watch": SzfbTeamWatchSerializer(
                    watch,
                    context=serializer_context,
                ).data,
                "standings": SzfbStandingRowSerializer(
                    standings,
                    many=True,
                    context=serializer_context,
                ).data,
                "standing_zones": SzfbStandingZoneSerializer(
                    standing_zones,
                    many=True,
                ).data,
                "results": SzfbMatchHistorySerializer(
                    results,
                    many=True,
                    context=serializer_context,
                ).data,
                "form": get_recent_form_for_watch(watch),
                "upcoming": SzfbMatchSerializer(
                    upcoming,
                    many=True,
                    context=serializer_context,
                ).data,
                "player_stats": SzfbPlayerStatSerializer(
                    player_stats,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class SzfbWatchNextMatchView(APIView):
    def get(self, request, watch_id):
        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition", "club"),
            id=watch_id,
        )
        team_brands = get_club_team_brands(watch.club)
        next_match = get_upcoming_matches(watch).first()

        if not next_match:
            return Response(
                {
                    "watch_id": watch.id,
                    "next_match": None,
                }
            )

        return Response(
            {
                "watch_id": watch.id,
                "next_match": SzfbMatchSerializer(
                    next_match,
                    context={
                        "request": request,
                        "team_brands": team_brands,
                    },
                ).data,
            }
        )


class SzfbWatchPlayerStatsView(ListAPIView):
    serializer_class = SzfbPlayerStatSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]

        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition", "club"),
            id=watch_id,
        )

        return (
            watch.player_stats
            .select_related("club_player")
            .order_by("club_player__display_order", "rank", "player_name")
        )


class AdminClubPlayerPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 10


class AdminSzfbPlayerStatsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class AdminClubPlayerListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AdminClubPlayerSerializer
    pagination_class = AdminClubPlayerPagination

    def get_queryset(self):
        club_slug = self.request.query_params.get("club")
        watch_id = self.request.query_params.get("watch")
        season = self.request.query_params.get("season")
        search = self.request.query_params.get("search", "").strip()
        active = self.request.query_params.get("active")

        queryset = (
            ClubPlayer.objects
            .select_related("club")
            .prefetch_related(
                "szfb_stats",
                "szfb_stats__watched_team",
                "szfb_stats__watched_team__competition",
            )
            .order_by("display_order", "full_name", "id")
        )

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)
        else:
            queryset = queryset.none()

        if watch_id:
            queryset = queryset.filter(szfb_stats__watched_team_id=watch_id)

        if season:
            queryset = queryset.filter(
                szfb_stats__watched_team__competition__season=season,
            )

        if search:
            queryset = queryset.filter(full_name__icontains=search)

        if active == "true":
            queryset = queryset.filter(is_active=True)
        elif active == "false":
            queryset = queryset.filter(is_active=False)

        return queryset.distinct()


class AdminClubPlayerUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, player_id):
        player_queryset = ClubPlayer.objects.select_related("club").prefetch_related(
            "szfb_stats",
            "szfb_stats__watched_team",
            "szfb_stats__watched_team__competition",
        )

        club_slug = request.data.get("club_slug") or request.query_params.get("club")

        if club_slug:
            player_queryset = player_queryset.filter(club__slug=club_slug)

        player = get_object_or_404(player_queryset, id=player_id)

        data = {
            key: request.data.get(key)
            for key in request.data.keys()
            if key != "club_slug" and key != "photo"
        }

        if "photo" in request.FILES:
            data["photo"] = request.FILES["photo"]

        serializer = AdminClubPlayerUpdateSerializer(
            player,
            data=data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        player.refresh_from_db()
        schedule_revalidation(
            get_player_revalidation_paths(player),
            reason="ClubPlayer updated via admin API",
            club_slug=player.club.slug,
        )

        return Response(
            AdminClubPlayerSerializer(
                player,
                context={"request": request},
            ).data
        )
    def delete(self, request, player_id):
        player_queryset = ClubPlayer.objects.select_related("club").prefetch_related(
            "szfb_stats",
            "szfb_stats__watched_team",
            "szfb_stats__watched_team__competition",
        )

        club_slug = request.query_params.get("club")

        if club_slug:
            player_queryset = player_queryset.filter(club__slug=club_slug)

        player = get_object_or_404(player_queryset, id=player_id)

        revalidation_paths = get_player_revalidation_paths(player)
        club_slug = player.club.slug

        player.szfb_stats.all().delete()

        if player.photo:
            player.photo.delete(save=False)

        player.delete()

        schedule_revalidation(
            revalidation_paths,
            reason="ClubPlayer deleted via admin API",
            club_slug=club_slug,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminSzfbTeamWatchListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SzfbTeamWatchAdminSerializer

    def get_queryset(self):
        expire_stale_running_competition_syncs()

        queryset = (
            SzfbTeamWatch.objects
            .select_related("competition", "club")
            .order_by("label")
        )

        club_slug = self.request.query_params.get("club")

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        return queryset


class AdminSzfbCompetitionListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AdminSzfbCompetitionSerializer

    def get_queryset(self):
        expire_stale_running_competition_syncs()

        club_slug = self.request.query_params.get("club")
        season = self.request.query_params.get("season")

        watched_team_queryset = (
            SzfbTeamWatch.objects
            .select_related("club")
            .annotate(
                matches_count=Count("matches", distinct=True),
                finished_matches_count=Count(
                    "matches",
                    filter=Q(matches__match_type="finished"),
                    distinct=True,
                ),
                upcoming_matches_count=Count(
                    "matches",
                    filter=Q(matches__match_type="upcoming"),
                    distinct=True,
                ),
                player_stats_count=Count("player_stats", distinct=True),
                goalie_stats_count=Count("goalie_stats", distinct=True),
            )
            .order_by("label", "team_name")
        )

        queryset = SzfbCompetition.objects.all()
        watched_teams_count_filter = Q()

        if club_slug:
            queryset = queryset.filter(watched_teams__club__slug=club_slug)
            watched_team_queryset = watched_team_queryset.filter(club__slug=club_slug)
            watched_teams_count_filter = Q(watched_teams__club__slug=club_slug)

        if season:
            queryset = queryset.filter(season=season)

        return (
            queryset
            .annotate(
                standings_count=Count("standings", distinct=True),
                watched_teams_count=Count(
                    "watched_teams",
                    filter=watched_teams_count_filter,
                    distinct=True,
                ),
            )
            .prefetch_related(
                Prefetch("watched_teams", queryset=watched_team_queryset)
            )
            .distinct()
            .order_by("-season", "name")
        )


class AdminSzfbCompetitionStandingsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AdminSzfbStandingRowSerializer
    _club = None

    def get_club(self):
        if self._club is None:
            self._club = get_editor_club_or_404(
                self.request,
                self.request.query_params.get("club", ""),
            )
        return self._club

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]
        club = self.get_club()

        get_object_or_404(
            SzfbCompetition.objects.filter(
                watched_teams__club=club,
            ).distinct(),
            id=competition_id,
        )

        return (
            SzfbStandingRow.objects
            .filter(competition_id=competition_id)
            .order_by("position")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["team_brands"] = get_club_team_brands(self.get_club())
        return context


class AdminSzfbCompetitionStandingZonesView(APIView):
    permission_classes = [IsAuthenticated]

    def get_competition_and_club(self, request, competition_id):
        club_slug = request.data.get("club_slug") or request.query_params.get(
            "club",
            "",
        )
        club = get_editor_club_or_404(request, club_slug)
        competition = get_object_or_404(
            SzfbCompetition.objects.filter(
                watched_teams__club=club,
            ).distinct(),
            id=competition_id,
        )
        return competition, club

    def get(self, request, competition_id):
        competition, _club = self.get_competition_and_club(
            request,
            competition_id,
        )
        zones = competition.standing_zones.order_by(
            "display_order",
            "start_position",
            "id",
        )
        return Response(SzfbStandingZoneSerializer(zones, many=True).data)

    def put(self, request, competition_id):
        competition, club = self.get_competition_and_club(
            request,
            competition_id,
        )
        zones_data = request.data.get("zones")

        if not isinstance(zones_data, list):
            raise ValidationError({"zones": "Zóny musia byť zoznam."})

        validated_zones = []
        allowed_kinds = {
            SzfbStandingZone.KIND_PLAYOFF,
            SzfbStandingZone.KIND_BARAGE,
            SzfbStandingZone.KIND_RELEGATION,
        }

        for index, item in enumerate(zones_data):
            if not isinstance(item, dict):
                raise ValidationError(
                    {"zones": f"Zóna #{index + 1} má neplatný formát."}
                )

            kind = str(item.get("kind") or "").strip()
            label = str(item.get("label") or "").strip()

            if kind not in allowed_kinds:
                raise ValidationError(
                    {"zones": f"Zóna #{index + 1} má neplatný typ."}
                )
            if not label:
                raise ValidationError(
                    {"zones": f"Zóna #{index + 1} nemá názov."}
                )

            try:
                start_position = int(item.get("start_position"))
                end_position = int(item.get("end_position"))
                display_order = int(item.get("display_order", index))
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    {"zones": f"Zóna #{index + 1} má neplatné pozície."}
                ) from exc

            if start_position < 1 or end_position < 1:
                raise ValidationError(
                    {"zones": "Pozície v zónach musia byť kladné čísla."}
                )
            if start_position > end_position:
                raise ValidationError(
                    {
                        "zones": (
                            f"Zóna '{label}' má začiatok väčší než koniec."
                        )
                    }
                )

            validated_zones.append(
                {
                    "kind": kind,
                    "label": label,
                    "start_position": start_position,
                    "end_position": end_position,
                    "display_order": max(0, display_order),
                    "is_active": bool(item.get("is_active", True)),
                }
            )

        active_zones = sorted(
            [zone for zone in validated_zones if zone["is_active"]],
            key=lambda zone: (zone["start_position"], zone["end_position"]),
        )
        previous_end = 0
        for zone in active_zones:
            if zone["start_position"] <= previous_end:
                raise ValidationError(
                    {"zones": "Aktívne zóny sa nesmú prekrývať."}
                )
            previous_end = zone["end_position"]

        max_position = competition.standings.aggregate(
            max_position=Max("position")
        )["max_position"]
        if max_position:
            too_high = next(
                (
                    zone
                    for zone in active_zones
                    if zone["end_position"] > max_position
                ),
                None,
            )
            if too_high:
                raise ValidationError(
                    {
                        "zones": (
                            f"Zóna '{too_high['label']}' končí na pozícii "
                            f"{too_high['end_position']}, ale tabuľka má iba "
                            f"{max_position} tímov."
                        )
                    }
                )

        with transaction.atomic():
            competition.standing_zones.all().delete()
            SzfbStandingZone.objects.bulk_create(
                [
                    SzfbStandingZone(
                        competition=competition,
                        **zone,
                    )
                    for zone in validated_zones
                ]
            )

        schedule_competition_revalidation(
            competition,
            club,
            reason="SZFB standing zones updated via admin API",
        )

        zones = competition.standing_zones.order_by(
            "display_order",
            "start_position",
            "id",
        )
        return Response(SzfbStandingZoneSerializer(zones, many=True).data)


class AdminSzfbTeamBrandListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        club = get_editor_club_or_404(
            request,
            request.query_params.get("club", ""),
        )
        brands = SzfbTeamBrand.objects.filter(club=club).select_related(
            "competition",
            "branding_source__competition",
            "branding_source__branding_source",
        ).order_by(
            "team_name",
            "id",
        )
        return Response(
            SzfbTeamBrandSerializer(
                brands,
                many=True,
                context={"request": request},
            ).data
        )

    def post(self, request):
        club_slug = request.data.get("club_slug") or request.query_params.get(
            "club",
            "",
        )
        club = get_editor_club_or_404(request, club_slug)

        data = {
            key: request.data.get(key)
            for key in request.data.keys()
            if key not in {"club_slug", "logo"}
        }
        if "logo" in request.FILES:
            data["logo"] = request.FILES["logo"]

        serializer = AdminSzfbTeamBrandWriteSerializer(
            data=data,
            context={
                "request": request,
                "club": club,
            },
        )
        serializer.is_valid(raise_exception=True)
        brand = serializer.save()

        schedule_team_brand_revalidation(
            club,
            reason="SZFB team brand created via admin API",
        )

        return Response(
            SzfbTeamBrandSerializer(
                brand,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


class AdminSzfbTeamBrandDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_brand(self, request, brand_id):
        club_slug = request.data.get("club_slug") or request.query_params.get(
            "club",
            "",
        )
        club = get_editor_club_or_404(request, club_slug)
        brand = get_object_or_404(
            SzfbTeamBrand.objects.select_related(
                "club",
                "competition",
                "branding_source__competition",
                "branding_source__branding_source",
            ),
            id=brand_id,
            club=club,
        )
        return club, brand

    def patch(self, request, brand_id):
        club, brand = self.get_brand(request, brand_id)
        data = {
            key: request.data.get(key)
            for key in request.data.keys()
            if key not in {"club_slug", "logo"}
        }
        if "logo" in request.FILES:
            data["logo"] = request.FILES["logo"]

        serializer = AdminSzfbTeamBrandWriteSerializer(
            brand,
            data=data,
            partial=True,
            context={
                "request": request,
                "club": club,
            },
        )
        serializer.is_valid(raise_exception=True)
        brand = serializer.save()

        schedule_team_brand_revalidation(
            club,
            reason="SZFB team brand updated via admin API",
        )

        return Response(
            SzfbTeamBrandSerializer(
                brand,
                context={"request": request},
            ).data
        )

    def delete(self, request, brand_id):
        club, brand = self.get_brand(request, brand_id)
        delete_team_brand_logo_if_unreferenced(brand)
        brand.delete()

        schedule_team_brand_revalidation(
            club,
            reason="SZFB team brand deleted via admin API",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminSzfbWatchMatchesView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AdminSzfbMatchSerializer
    _watch = None

    def get_watch(self):
        if self._watch is None:
            self._watch = get_editor_watch_or_404(
                self.request,
                self.kwargs["watch_id"],
            )
        return self._watch

    def get_queryset(self):
        watch = self.get_watch()
        queryset = SzfbMatch.objects.filter(watched_team=watch)
        match_type = self.request.query_params.get("type")

        if match_type in {"finished", "upcoming"}:
            queryset = queryset.filter(match_type=match_type)

        return queryset.order_by("match_date", "match_time", "id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["team_brands"] = get_club_team_brands(self.get_watch().club)
        return context


class AdminSzfbWatchPlayersView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AdminSzfbPlayerStatSerializer
    pagination_class = AdminSzfbPlayerStatsPagination

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]
        club_slug = self.request.query_params.get("club")

        watch_queryset = SzfbTeamWatch.objects.all()

        if club_slug:
            watch_queryset = watch_queryset.filter(club__slug=club_slug)

        get_object_or_404(watch_queryset, id=watch_id)

        return (
            SzfbPlayerStat.objects
            .select_related(
                "club_player",
                "watched_team",
                "watched_team__club",
                "watched_team__competition",
            )
            .filter(watched_team_id=watch_id)
            .order_by("club_player__display_order", "rank", "player_name", "id")
        )


class AdminSzfbWatchGoaliesView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AdminSzfbGoalieStatSerializer
    pagination_class = AdminSzfbPlayerStatsPagination

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]
        club_slug = self.request.query_params.get("club")
        watch_queryset = SzfbTeamWatch.objects.all()

        if club_slug:
            watch_queryset = watch_queryset.filter(club__slug=club_slug)

        get_object_or_404(watch_queryset, id=watch_id)
        return (
            SzfbGoalieStat.objects.select_related(
                "club_player",
                "watched_team",
                "watched_team__club",
                "watched_team__competition",
            )
            .filter(watched_team_id=watch_id)
            .order_by("club_player__display_order", "rank", "player_name", "id")
        )


class AdminSzfbCompetitionSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, competition_id):
        competition = get_object_or_404(
            SzfbCompetition,
            id=competition_id,
        )

        can_start, reason, next_allowed_at = can_start_competition_sync(
            competition,
            user=request.user,
        )

        if not can_start:
            response_status = status.HTTP_400_BAD_REQUEST

            if reason in ["already_running", "rate_limited"]:
                response_status = status.HTTP_409_CONFLICT

            return Response(
                {
                    "status": "blocked",
                    "reason": reason,
                    "next_allowed_at": next_allowed_at,
                },
                status=response_status,
            )

        now = timezone.now()

        SzfbCompetition.objects.filter(id=competition.id).update(
            sync_status=SzfbCompetition.SYNC_STATUS_RUNNING,
            sync_started_at=now,
            sync_last_attempt_at=now,
            sync_finished_at=None,
            sync_error="",
        )

        try:
            Thread(
                target=run_competition_sync,
                args=(competition.id,),
                daemon=True,
            ).start()
        except Exception as exc:
            SzfbCompetition.objects.filter(id=competition.id).update(
                sync_status=SzfbCompetition.SYNC_STATUS_ERROR,
                sync_finished_at=timezone.now(),
                sync_error=str(exc)[:5000],
            )
            raise

        return Response(
            {
                "status": "started",
                "competition_id": competition.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AdminSzfbPlayerStatUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, player_id):
        player_queryset = SzfbPlayerStat.objects.select_related(
            "club_player",
            "watched_team",
            "watched_team__club",
            "watched_team__competition",
        )

        club_slug = request.data.get("club_slug")

        if club_slug:
            player_queryset = player_queryset.filter(
                watched_team__club__slug=club_slug,
            )

        player = get_object_or_404(
            player_queryset,
            id=player_id,
        )

        data = {
            key: request.data.get(key)
            for key in request.data.keys()
            if key not in {"club_slug", "photo"}
        }

        if "photo" in request.FILES:
            data["photo"] = request.FILES["photo"]

        serializer = AdminSzfbPlayerStatUpdateSerializer(
            player,
            data=data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        player.refresh_from_db()
        schedule_revalidation(
            get_player_stat_revalidation_paths(player),
            reason="SZFB player updated via admin API",
            club_slug=player.watched_team.club.slug,
        )

        return Response(
            AdminSzfbPlayerStatSerializer(
                player,
                context={"request": request},
            ).data
        )


class AdminSzfbWatchSettingsCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AdminSzfbWatchSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        watch = serializer.save()
        if not watch.is_active:
            SzfbWatchAutoSyncConfig.objects.filter(watch=watch).update(
                is_enabled=False
            )
        schedule_revalidation(
            get_watch_revalidation_paths(watch),
            reason="SZFB team watch created via admin API",
            club_slug=watch.club.slug,
        )

        return Response(
            AdminSzfbWatchSettingsSerializer(watch).data,
            status=status.HTTP_201_CREATED,
        )


class AdminSzfbWatchSettingsUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, watch_id):
        watch_queryset = SzfbTeamWatch.objects.select_related(
            "competition",
            "club",
        )

        club_slug = request.data.get("club_slug")

        if club_slug:
            watch_queryset = watch_queryset.filter(club__slug=club_slug)

        watch = get_object_or_404(
            watch_queryset,
            id=watch_id,
        )
        old_paths = get_watch_revalidation_paths(watch)

        serializer = AdminSzfbWatchSettingsSerializer(
            watch,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        watch = serializer.save()
        if not watch.is_active:
            SzfbWatchAutoSyncConfig.objects.filter(watch=watch).update(
                is_enabled=False
            )
        schedule_revalidation(
            [*old_paths, *get_watch_revalidation_paths(watch)],
            reason="SZFB team watch updated via admin API",
            club_slug=watch.club.slug,
        )

        return Response(AdminSzfbWatchSettingsSerializer(watch).data)
class AdminSzfbWatchDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, watch_id):
        watch = get_editor_watch_or_404(request, watch_id)
        club_slug = watch.club.slug
        paths = get_watch_revalidation_paths(watch)
        watch.delete()
        schedule_revalidation(
            paths,
            reason="SZFB team watch deleted via admin API",
            club_slug=club_slug,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminSzfbWatchAutoSyncConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get_config(self, request, watch_id):
        watch = get_editor_watch_or_404(request, watch_id)
        config, created = SzfbWatchAutoSyncConfig.objects.get_or_create(
            watch=watch,
            defaults={
                "is_enabled": False,
                "frequency": SzfbWatchAutoSyncConfig.FREQUENCY_WEEKLY,
                "weekday": SzfbWatchAutoSyncConfig.WEEKDAY_MONDAY,
            },
        )
        if created or not config.next_run_at:
            config.refresh_next_run_at()
        return config

    def get(self, request, watch_id):
        config = self.get_config(request, watch_id)
        return Response(AdminSzfbWatchAutoSyncConfigSerializer(config).data)

    def patch(self, request, watch_id):
        config = self.get_config(request, watch_id)
        serializer = AdminSzfbWatchAutoSyncConfigSerializer(
            config,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
