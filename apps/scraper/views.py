from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scraper.models import SzfbTeamWatch
from apps.scraper.serializers import (
    SzfbMatchSerializer,
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
        watch = SzfbTeamWatch.objects.select_related("competition").get(id=watch_id)
        return watch.competition.standings.order_by("position")


class SzfbWatchResultsView(ListAPIView):
    serializer_class = SzfbMatchSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]
        return (
            SzfbTeamWatch.objects.get(id=watch_id)
            .matches.filter(match_type="finished")
            .order_by("-match_date", "-match_time")
        )


class SzfbWatchUpcomingView(ListAPIView):
    serializer_class = SzfbMatchSerializer

    def get_queryset(self):
        watch_id = self.kwargs["watch_id"]
        return (
            SzfbTeamWatch.objects.get(id=watch_id)
            .matches.filter(match_type="upcoming")
            .order_by("match_date", "match_time")
        )


class SzfbWatchDashboardView(APIView):
    def get(self, request, watch_id):
        watch = SzfbTeamWatch.objects.select_related("competition").get(id=watch_id)

        standings = watch.competition.standings.order_by("position")
        results = watch.matches.filter(match_type="finished").order_by("-match_date", "-match_time")[:8]
        upcoming = watch.matches.filter(match_type="upcoming").order_by("match_date", "match_time")[:8]

        return Response(
            {
                "watch": SzfbTeamWatchSerializer(watch).data,
                "standings": SzfbStandingRowSerializer(standings, many=True).data,
                "results": SzfbMatchSerializer(results, many=True).data,
                "upcoming": SzfbMatchSerializer(upcoming, many=True).data,
            }
        )