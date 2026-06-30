from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.clubs.models import ClubMembership
from apps.common.permissions import EDITOR_ROLES

from .admin_serializers import AdminCategorySerializer
from .models import Category


class AdminCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        club_ids = ClubMembership.objects.filter(
            user=self.request.user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = Category.objects.filter(
            club_id__in=club_ids,
            is_active=True,
        ).select_related("club").order_by("club__name", "order", "name")

        club_slug = self.request.query_params.get("club")
        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        return queryset
