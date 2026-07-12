from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import (
    Page,
    PageSection,
    PageSectionContactItem,
    PageSectionItem,
    SECTION_CHOICES_BY_PAGE_TYPE,
    create_default_page_sections,
)
from .revalidation import revalidate_page, revalidate_page_section
from .admin_serializers import (
    AdminPageSectionContactItemSerializer,
    AdminPageSectionItemSerializer,
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

        if not instance.is_deletable:
            raise PermissionDenied("Túto systémovú stránku nie je možné odstrániť.")

        page = instance
        instance.delete()
        revalidate_page(page, reason="Page deleted via admin API")

    @action(detail=False, methods=["get"], url_path="section-options")
    def section_options(self, request):
        page_id = request.query_params.get("page")

        if not page_id:
            return Response(
                {"detail": "Chýba parameter page."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        page = self.get_queryset().filter(id=page_id).first()

        if not page:
            return Response(
                {"detail": "Stránka neexistuje alebo k nej nemáš oprávnenie."},
                status=status.HTTP_404_NOT_FOUND,
            )

        allowed_section_types = SECTION_CHOICES_BY_PAGE_TYPE.get(
            page.page_type,
            [],
        )
        labels_by_value = dict(PageSection.SECTION_TYPE_CHOICES)
        items = [
            {
                "value": section_type,
                "label": labels_by_value.get(section_type, section_type),
            }
            for section_type in allowed_section_types
        ]

        return Response(
            {
                "page_type": page.page_type,
                "items": items,
            },
            status=status.HTTP_200_OK,
        )


class AdminPageSectionViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPageSectionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

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

    @action(detail=False, methods=["patch"], url_path="reorder")
    def reorder(self, request):
        items = request.data.get("items")

        if not isinstance(items, list) or not items:
            return Response(
                {"detail": "Pošli neprázdny zoznam sekcií v poli items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        section_ids = []
        orders_by_id = {}

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict) or "id" not in item:
                return Response(
                    {"detail": "Každá položka musí obsahovať id sekcie."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                section_id = int(item["id"])
                order = int(item.get("order", index))
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Hodnoty id a order musia byť čísla."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            section_ids.append(section_id)
            orders_by_id[section_id] = order

        if len(set(section_ids)) != len(section_ids):
            return Response(
                {"detail": "Zoznam sekcií obsahuje duplicitné id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sections = list(self.get_queryset().filter(id__in=section_ids))

        if len(sections) != len(section_ids):
            return Response(
                {"detail": "Niektoré sekcie neexistujú alebo k nim nemáš oprávnenie."},
                status=status.HTTP_403_FORBIDDEN,
            )

        page_ids = {section.page_id for section in sections}
        if len(page_ids) != 1:
            return Response(
                {"detail": "Všetky sekcie musia patriť k jednej stránke."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sections_by_id = {section.id: section for section in sections}
        ordered_sections = [
            sections_by_id[section_id]
            for section_id in sorted(section_ids, key=lambda item_id: orders_by_id[item_id])
        ]

        with transaction.atomic():
            for order, section in enumerate(ordered_sections, start=1):
                section.order = order
                section.save(update_fields=["order", "updated_at"])

        revalidate_page_section(
            ordered_sections[0],
            reason="PageSections reordered via admin API",
        )

        serializer = self.get_serializer(ordered_sections, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminPageSectionItemViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPageSectionItemSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = PageSectionItem.objects.filter(
            section__page__club_id__in=club_ids
        ).select_related("section", "section__page", "section__page__club").order_by(
            "section__page__club__name",
            "section__page__title",
            "section__order",
            "order",
            "id",
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
        if section.section_type not in {"custom_documents", "custom_links"}:
            raise PermissionDenied(
                "Položka môže patriť iba ku sekcii Vlastné dokumenty alebo Vlastné odkazy."
            )

        if not user_has_club_role(self.request.user, section.page.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať položky tejto sekcie.")

    def perform_create(self, serializer):
        section = serializer.validated_data["section"]
        self._validate_section_permission(section)
        item = serializer.save()
        revalidate_page_section(
            item.section,
            reason="PageSectionItem created via admin API",
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        self._validate_section_permission(instance.section)
        section = serializer.validated_data.get("section", instance.section)
        self._validate_section_permission(section)
        item = serializer.save()
        revalidate_page_section(
            item.section,
            reason="PageSectionItem updated via admin API",
        )

    def perform_destroy(self, instance):
        self._validate_section_permission(instance.section)
        section = instance.section
        instance.delete()
        revalidate_page_section(
            section,
            reason="PageSectionItem deleted via admin API",
        )

    @action(detail=False, methods=["patch"], url_path="reorder")
    def reorder(self, request):
        items = request.data.get("items")

        if not isinstance(items, list) or not items:
            return Response(
                {"detail": "Pošli neprázdny zoznam položiek v poli items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item_ids = []
        orders_by_id = {}

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict) or "id" not in item:
                return Response(
                    {"detail": "Každá položka musí obsahovať id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                item_id = int(item["id"])
                order = int(item.get("order", index))
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Hodnoty id a order musia byť čísla."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item_ids.append(item_id)
            orders_by_id[item_id] = order

        if len(set(item_ids)) != len(item_ids):
            return Response(
                {"detail": "Zoznam položiek obsahuje duplicitné id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        section_items = list(self.get_queryset().filter(id__in=item_ids))

        if len(section_items) != len(item_ids):
            return Response(
                {"detail": "Niektoré položky neexistujú alebo k nim nemáš oprávnenie."},
                status=status.HTTP_403_FORBIDDEN,
            )

        section_ids = {item.section_id for item in section_items}
        if len(section_ids) != 1:
            return Response(
                {"detail": "Všetky položky musia patriť k jednej sekcii."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_by_id = {item.id: item for item in section_items}
        ordered_items = [
            items_by_id[item_id]
            for item_id in sorted(item_ids, key=lambda item_id: orders_by_id[item_id])
        ]

        with transaction.atomic():
            for order, item in enumerate(ordered_items, start=1):
                item.order = order
                item.save(update_fields=["order", "updated_at"])

        revalidate_page_section(
            ordered_items[0].section,
            reason="PageSectionItems reordered via admin API",
        )

        serializer = self.get_serializer(ordered_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
            "id",
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