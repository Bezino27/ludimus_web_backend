from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clubs.models import ClubMembership
from apps.common.permissions import EDITOR_ROLES, user_has_club_role

from .admin_serializers import AdminPartnerSerializer
from .models import Partner
from .ordering import get_next_partner_order, normalize_partner_group
from .revalidation import revalidate_partner_paths


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

        queryset = (
            Partner.objects.filter(club_id__in=club_ids)
            .select_related("club")
            .ordered_for_admin()
        )

        club_slug = self.request.query_params.get("club")
        is_active = self.request.query_params.get("is_active")
        tier = self.request.query_params.get("tier")

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        if is_active is not None:
            normalized_is_active = is_active.lower()
            if normalized_is_active == "true":
                queryset = queryset.filter(is_active=True)
            elif normalized_is_active == "false":
                queryset = queryset.filter(is_active=False)

        if tier is not None:
            normalized_tier = tier.strip().lower()
            if normalized_tier in {"none", "ungrouped"}:
                normalized_tier = Partner.TIER_UNGROUPED
            queryset = queryset.filter(tier=normalized_tier)

        return queryset

    @staticmethod
    def _lock_clubs(*clubs):
        clubs = [club for club in clubs if club is not None]
        if not clubs:
            return

        club_model = clubs[0].__class__
        club_ids = sorted({club.pk for club in clubs})

        list(
            club_model.objects.select_for_update()
            .filter(pk__in=club_ids)
            .order_by("pk")
        )

    @transaction.atomic
    def perform_create(self, serializer):
        club = serializer.validated_data["club"]
        if not user_has_club_role(self.request.user, club, EDITOR_ROLES):
            raise PermissionDenied(
                "Nemáš oprávnenie vytvárať partnerov pre tento klub."
            )

        self._lock_clubs(club)

        tier = serializer.validated_data.get(
            "tier",
            Partner.TIER_UNGROUPED,
        )
        order = get_next_partner_order(
            club.pk,
            tier,
            lock=True,
        )

        partner = serializer.save(order=order)
        revalidate_partner_paths(
            partner,
            reason="Partner created via admin API",
        )

    @transaction.atomic
    def perform_update(self, serializer):
        instance = self.get_object()

        if not user_has_club_role(
            self.request.user,
            instance.club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie upravovať tohto partnera."
            )

        old_club = instance.club
        old_club_id = instance.club_id
        old_tier = instance.tier

        new_club = serializer.validated_data.get("club", old_club)
        new_tier = serializer.validated_data.get("tier", old_tier)

        if not user_has_club_role(
            self.request.user,
            new_club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie presunúť partnera do tohto klubu."
            )

        self._lock_clubs(old_club, new_club)

        group_changed = (
            old_club_id != new_club.pk
            or old_tier != new_tier
        )

        if group_changed:
            new_order = get_next_partner_order(
                new_club.pk,
                new_tier,
                lock=True,
            )
            partner = serializer.save(order=new_order)

            normalize_partner_group(
                old_club_id,
                old_tier,
                lock=True,
            )
            normalize_partner_group(
                partner.club_id,
                partner.tier,
                lock=True,
            )
        else:
            partner = serializer.save()

        revalidate_partner_paths(
            partner,
            reason="Partner updated via admin API",
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        if not user_has_club_role(
            self.request.user,
            instance.club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie zmazať tohto partnera."
            )

        club = instance.club
        club_id = instance.club_id
        tier = instance.tier

        self._lock_clubs(club)

        partner = instance
        instance.delete()

        normalize_partner_group(
            club_id,
            tier,
            lock=True,
        )

        revalidate_partner_paths(
            partner,
            reason="Partner deleted via admin API",
        )

    @action(detail=False, methods=["get"], url_path="tiers")
    def tiers(self, request):
        return Response(
            [
                {
                    "value": Partner.TIER_UNGROUPED,
                    "label": Partner.UNGROUPED_LABEL,
                },
                *[
                    {
                        "value": value,
                        "label": label,
                    }
                    for value, label in Partner.Tier.choices
                ],
            ]
        )

    @action(detail=True, methods=["post"], url_path="move")
    @transaction.atomic
    def move(self, request, pk=None):
        direction = str(request.data.get("direction", "")).lower()
        if direction not in {"up", "down"}:
            raise ValidationError(
                {
                    "direction": (
                        "Povolená hodnota je 'up' alebo 'down'."
                    )
                }
            )

        partner = self.get_object()

        if not user_has_club_role(
            request.user,
            partner.club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie meniť poradie tohto partnera."
            )

        self._lock_clubs(partner.club)

        partners = normalize_partner_group(
            partner.club_id,
            partner.tier,
            lock=True,
        )

        current_index = next(
            (
                index
                for index, item in enumerate(partners)
                if item.pk == partner.pk
            ),
            None,
        )

        if current_index is None:
            raise ValidationError(
                "Partner sa v danej skupine nenašiel."
            )

        target_index = (
            current_index - 1
            if direction == "up"
            else current_index + 1
        )

        partner = partners[current_index]

        if target_index < 0 or target_index >= len(partners):
            serializer = self.get_serializer(partner)
            return Response(
                {
                    "moved": False,
                    "partner": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        target = partners[target_index]
        partner.order, target.order = target.order, partner.order

        Partner.objects.bulk_update(
            [partner, target],
            ["order"],
        )

        partner.refresh_from_db()

        revalidate_partner_paths(
            partner,
            reason="Partner order changed via admin API",
        )

        serializer = self.get_serializer(partner)
        return Response(
            {
                "moved": True,
                "partner": serializer.data,
            },
            status=status.HTTP_200_OK,
        )