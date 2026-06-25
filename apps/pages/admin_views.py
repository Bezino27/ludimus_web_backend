from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Page, PageSection, create_default_page_sections
from .revalidation import revalidate_page, revalidate_page_section
from .admin_serializers import AdminPageSerializer, AdminPageSectionSerializer
from apps.clubs.models import ClubMembership
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPageViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = Page.objects.filter(
            club_id__in=club_ids
        ).select_related("club").order_by("navigation_order", "title")

        club_slug = self.request.query_params.get("club")
        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data["club"]
        if not user_has_club_role(self.request.user, club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie vytvárať stránky pre tento klub.")
        page = serializer.save()
        defaults_created = create_default_page_sections(page)
        revalidate_page(page, reason="Page created via admin API")
        if defaults_created:
            revalidate_page(page, reason="Default PageSections created via admin API")

    def perform_update(self, serializer):
        instance = self.get_object()
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať túto stránku.")
        page = serializer.save()
        defaults_created = create_default_page_sections(page)
        revalidate_page(page, reason="Page updated via admin API")
        if defaults_created:
            revalidate_page(page, reason="Default PageSections created via admin API")

    def perform_destroy(self, instance):
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie zmazať túto stránku.")
        page = instance
        instance.delete()
        revalidate_page(page, reason="Page deleted via admin API")


class AdminPageSectionViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPageSectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = PageSection.objects.filter(
            page__club_id__in=club_ids
        ).select_related("page", "page__club").order_by(
            "page__club__name",
            "page__title",
            "order",
        )

        club_slug = self.request.query_params.get("club")
        if club_slug:
            queryset = queryset.filter(page__club__slug=club_slug)

        page_id = self.request.query_params.get("page")
        if page_id:
            queryset = queryset.filter(page_id=page_id)

        return queryset

    def perform_create(self, serializer):
        page = serializer.validated_data["page"]
        if not user_has_club_role(self.request.user, page.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie vytvárať sekcie pre túto stránku.")
        section = serializer.save()
        revalidate_page_section(section, reason="PageSection created via admin API")

    def perform_update(self, serializer):
        instance = self.get_object()
        if not user_has_club_role(self.request.user, instance.page.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať túto sekciu.")
        section = serializer.save()
        revalidate_page_section(section, reason="PageSection updated via admin API")

    def perform_destroy(self, instance):
        if not user_has_club_role(self.request.user, instance.page.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie zmazať túto sekciu.")
        section = instance
        instance.delete()
        revalidate_page_section(section, reason="PageSection deleted via admin API")
