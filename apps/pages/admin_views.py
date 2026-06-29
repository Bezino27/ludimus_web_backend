from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import (
    Page,
    PageSection,
    PageSectionContactItem,
    create_default_page_sections,
)
from .revalidation import revalidate_page, revalidate_page_section
from .admin_serializers import (
    AdminPageSectionContactItemSerializer,
    AdminPageSectionSerializer,
    AdminPageSerializer,
)
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


class AdminPageSectionContactItemViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPageSectionContactItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = PageSectionContactItem.objects.filter(
            section__page__club_id__in=club_ids
        ).select_related("section", "section__page", "section__page__club").order_by(
            "section__page__club__name",
            "section__page__title",
            "section__order",
            "order",
        )

        club_slug = self.request.query_params.get("club")
        if club_slug:
            queryset = queryset.filter(section__page__club__slug=club_slug)

        page_id = self.request.query_params.get("page")
        if page_id:
            queryset = queryset.filter(section__page_id=page_id)

        section_id = self.request.query_params.get("section")
        if section_id:
            queryset = queryset.filter(section_id=section_id)

        return queryset

    def _validate_section_permission(self, section):
        if section.section_type != "contact":
            raise PermissionDenied(
                "Kontaktná položka môže patriť iba ku kontaktnej sekcii stránky."
            )

        if not user_has_club_role(self.request.user, section.page.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať kontakt tejto sekcie.")

    def perform_create(self, serializer):
        section = serializer.validated_data["section"]
        self._validate_section_permission(section)
        item = serializer.save()
        revalidate_page_section(
            item.section,
            reason="PageSectionContactItem created via admin API",
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        self._validate_section_permission(instance.section)
        section = serializer.validated_data.get("section", instance.section)
        self._validate_section_permission(section)
        item = serializer.save()
        revalidate_page_section(
            item.section,
            reason="PageSectionContactItem updated via admin API",
        )

    def perform_destroy(self, instance):
        self._validate_section_permission(instance.section)
        section = instance.section
        instance.delete()
        revalidate_page_section(
            section,
            reason="PageSectionContactItem deleted via admin API",
        )
