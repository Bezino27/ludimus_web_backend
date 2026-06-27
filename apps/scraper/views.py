from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scraper.models import SzfbTeamWatch
from apps.scraper.serializers import (
    SzfbMatchSerializer,
    SzfbPlayerStatSerializer,
    SzfbStandingRowSerializer,
    SzfbTeamWatchSerializer,
)


class SzfbTeamWatchDetailView(RetrieveAPIView):
    queryset = SzfbTeamWatch.objects.select_related("competition")
    serializer_class = SzfbTeamWatchSerializer


class SzfbWatchStandingsView(ListAPIView):
    serializer_class = SzfbStandingRowSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]

        watch = get_object_or_404(
            SzfbTeamWatch.objects.select_related("competition"),
            id=watch_id,
        )

        return watch.competition.standings.order_by("position")


class SzfbWatchResultsView(ListAPIView):
    serializer_class = SzfbMatchSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]

        watch = get_object_or_404(
            SzfbTeamWatch,
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
            SzfbTeamWatch,
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
            SzfbTeamWatch.objects.select_related("competition"),
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

        player_stats = watch.player_stats.order_by("rank")[:8]

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
                                                        ).data
            }
        )


class SzfbWatchNextMatchView(APIView):
    def get(self, request, watch_id):
        now = timezone.localtime()

        watch = get_object_or_404(
            SzfbTeamWatch,
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
            SzfbTeamWatch,
            id=watch_id,
        )

        return watch.player_stats.order_by("rank")