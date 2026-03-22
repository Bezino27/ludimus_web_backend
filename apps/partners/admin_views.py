from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Partner
from .admin_serializers import AdminPartnerSerializer
from apps.clubs.models import ClubMembership
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPartnerViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPartnerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = Partner.objects.filter(
            club_id__in=club_ids
        ).select_related("club").order_by("order", "name")

        club_slug = self.request.query_params.get("club")
        is_active = self.request.query_params.get("is_active")
        tier = self.request.query_params.get("tier")

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        if is_active is not None:
            if is_active.lower() == "true":
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(is_active=False)

        if tier:
            queryset = queryset.filter(tier=tier)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data["club"]
        if not user_has_club_role(self.request.user, club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie vytvárať partnerov pre tento klub.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať tohto partnera.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie zmazať tohto partnera.")
        instance.delete()