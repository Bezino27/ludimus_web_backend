from django.db.models import Count, Prefetch, Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.clubs.models import ClubMembership
from apps.common.permissions import EDITOR_ROLES, user_has_club_role

from .admin_serializers import PollAdminSerializer
from .models import Poll, PollOption


class AdminPollViewSet(viewsets.ModelViewSet):
    serializer_class = PollAdminSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        options_queryset = PollOption.objects.annotate(
            votes_count=Count("votes")
        ).order_by("order", "id")

        queryset = (
            Poll.objects.select_related("club")
            .prefetch_related(Prefetch("options", queryset=options_queryset))
            .annotate(total_votes=Count("votes"))
            .order_by("-created_at")
        )

        if not (user.is_staff or user.is_superuser):
            club_ids = ClubMembership.objects.filter(
                user=user,
                is_active=True,
                role__in=EDITOR_ROLES,
            ).values_list("club_id", flat=True)
            queryset = queryset.filter(club_id__in=club_ids)

        club_value = self.request.query_params.get("club")

        if club_value:
            club_filter = Q(club__slug=club_value)

            if club_value.isdigit():
                club_filter |= Q(club_id=int(club_value))

            queryset = queryset.filter(club_filter)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data["club"]

        if not self._can_manage_club(club):
            raise PermissionDenied("Nemáš oprávnenie vytvárať ankety pre tento klub.")

        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()

        if not self._can_manage_club(instance.club):
            raise PermissionDenied("Nemáš oprávnenie upravovať túto anketu.")

        new_club = serializer.validated_data.get("club")

        if new_club and not self._can_manage_club(new_club):
            raise PermissionDenied("Nemáš oprávnenie presunúť anketu do tohto klubu.")

        serializer.save()

    def perform_destroy(self, instance):
        if not self._can_manage_club(instance.club):
            raise PermissionDenied("Nemáš oprávnenie zmazať túto anketu.")

        instance.delete()

    def _can_manage_club(self, club):
        user = self.request.user

        if user.is_staff or user.is_superuser:
            return True

        return user_has_club_role(user, club, EDITOR_ROLES)
