from threading import Thread

from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scraper.models import (
    ClubPlayer,
    SzfbCompetition,
    SzfbMatch,
    SzfbPlayerStat,
    SzfbAutoSyncConfig,
    SzfbStandingRow,
    SzfbTeamWatch,
)
from apps.scraper.serializers import (
    AdminClubPlayerSerializer,
    AdminClubPlayerUpdateSerializer,
    AdminSzfbCompetitionSerializer,
    AdminSzfbMatchSerializer,
    AdminSzfbPlayerStatSerializer,
    AdminSzfbAutoSyncConfigSerializer,
    AdminSzfbPlayerStatUpdateSerializer,
    AdminSzfbStandingRowSerializer,
    AdminSzfbWatchSettingsSerializer,
    SzfbMatchSerializer,
    SzfbPlayerStatSerializer,
    SzfbStandingRowSerializer,
    SzfbTeamWatchAdminSerializer,
    SzfbTeamWatchSerializer,
)
from apps.scraper.services.szfb_sync_runner import (
    can_start_competition_sync,
    expire_stale_running_competition_syncs,
    run_competition_sync,
)


class SzfbTeamWatchDetailView(RetrieveAPIView):
    queryset = SzfbTeamWatch.objects.select_related("competition", "club")
    serializer_class = SzfbTeamWatchSerializer


class SzfbWatchStandingsView(ListAPIView):
    serializer_class = SzfbStandingRowSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]

        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition", "club"),
            id=watch_id,
        )

        return watch.competition.standings.order_by("position")


class SzfbWatchResultsView(ListAPIView):
    serializer_class = SzfbMatchSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]

        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition", "club"),
            id=watch_id,
        )

        return (
            watch.matches
            .filter(match_type="finished")
            .order_by("-match_date", "-match_time")
        )


class SzfbWatchUpcomingView(ListAPIView):
    serializer_class = SzfbMatchSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]

        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition", "club"),
            id=watch_id,
        )

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

        standings = watch.competition.standings.order_by("position")

        results = (
            watch.matches
            .filter(match_type="finished")
            .order_by("-match_date", "-match_time")[:8]
        )

        upcoming = (
            watch.matches
            .filter(match_type="upcoming")
            .order_by("match_date", "match_time")[:8]
        )

        player_stats = (
            watch.player_stats
            .select_related("club_player")
            .order_by("club_player__display_order", "rank", "player_name")[:8]
        )

        return Response(
            {
                "watch": SzfbTeamWatchSerializer(watch).data,
                "standings": SzfbStandingRowSerializer(standings, many=True).data,
                "results": SzfbMatchSerializer(results, many=True).data,
                "upcoming": SzfbMatchSerializer(upcoming, many=True).data,
                "player_stats": SzfbPlayerStatSerializer(
                    player_stats,
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class SzfbWatchNextMatchView(APIView):
    def get(self, request, watch_id):
        now = timezone.localtime()

        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition", "club"),
            id=watch_id,
        )

        next_match = (
            watch.matches
            .filter(match_type="upcoming")
            .filter(
                Q(match_date__gt=now.date())
                | Q(match_date=now.date(), match_time__gte=now.time())
            )
            .order_by("match_date", "match_time")
            .first()
        )

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
                "next_match": SzfbMatchSerializer(next_match).data,
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

        return Response(
            AdminClubPlayerSerializer(
                player,
                context={"request": request},
            ).data
        )


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

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]
        club_slug = self.request.query_params.get("club")

        competition_queryset = SzfbCompetition.objects.all()

        if club_slug:
            competition_queryset = competition_queryset.filter(
                watched_teams__club__slug=club_slug,
            )

        get_object_or_404(
            competition_queryset.distinct(),
            id=competition_id,
        )

        return (
            SzfbStandingRow.objects
            .filter(competition_id=competition_id)
            .order_by("position")
        )


class AdminSzfbWatchMatchesView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AdminSzfbMatchSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]
        club_slug = self.request.query_params.get("club")

        watch_queryset = SzfbTeamWatch.objects.all()

        if club_slug:
            watch_queryset = watch_queryset.filter(club__slug=club_slug)

        get_object_or_404(watch_queryset, id=watch_id)

        queryset = SzfbMatch.objects.filter(watched_team_id=watch_id)
        match_type = self.request.query_params.get("type")

        if match_type in {"finished", "upcoming"}:
            queryset = queryset.filter(match_type=match_type)

        return queryset.order_by("match_date", "match_time", "id")


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


class AdminSzfbCompetitionSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, competition_id):
        competition = get_object_or_404(
            SzfbCompetition,
            id=competition_id,
        )

        can_start, reason, next_allowed_at = can_start_competition_sync(
            competition,
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

        data = request.data.copy()
        data.pop("club_slug", None)

        serializer = AdminSzfbPlayerStatUpdateSerializer(
            player,
            data=data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        player.refresh_from_db()

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

        serializer = AdminSzfbWatchSettingsSerializer(
            watch,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        watch = serializer.save()

        return Response(AdminSzfbWatchSettingsSerializer(watch).data)
class AdminSzfbAutoSyncConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get_config(self, club_slug):
        if not club_slug:
            return None

        from apps.clubs.models import Club

        club = get_object_or_404(Club, slug=club_slug)

        config, created = SzfbAutoSyncConfig.objects.get_or_create(
            club=club,
            defaults={
                "is_enabled": False,
                "frequency": SzfbAutoSyncConfig.FREQUENCY_WEEKLY,
                "weekday": SzfbAutoSyncConfig.WEEKDAY_MONDAY,
            },
        )

        if created or not config.next_run_at:
            config.refresh_next_run_at()

        return config

    def get(self, request):
        club_slug = request.query_params.get("club", "")
        config = self.get_config(club_slug)

        if not config:
            return Response(
                {"detail": "Chýba club query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            AdminSzfbAutoSyncConfigSerializer(config).data
        )

    def patch(self, request):
        club_slug = request.data.get("club_slug") or request.query_params.get("club", "")
        config = self.get_config(club_slug)

        if not config:
            return Response(
                {"detail": "Chýba club_slug."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminSzfbAutoSyncConfigSerializer(
            config,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)