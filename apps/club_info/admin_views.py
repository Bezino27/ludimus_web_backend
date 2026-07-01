from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clubs.models import ClubMembership
from apps.common.permissions import EDITOR_ROLES, user_has_club_role
from apps.common.revalidation import revalidate_paths

from .models import ContactInfo, ClubDocument, ClubLink
from .admin_serializers import (
    AdminContactInfoSerializer,
    AdminClubDocumentSerializer,
    AdminClubLinkSerializer,
)


def get_editor_membership(user):
    return (
        ClubMembership.objects.select_related("club")
        .filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
            club__is_active=True,
        )
        .first()
    )


def get_editor_club_or_response(user):
    membership = get_editor_membership(user)

    if not membership:
        return None, Response(
            {"detail": "Nemáš oprávnenie spravovať klubové informácie."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return membership.club, None


def get_allowed_club_ids(user):
    return ClubMembership.objects.filter(
        user=user,
        is_active=True,
        role__in=EDITOR_ROLES,
        club__is_active=True,
    ).values_list("club_id", flat=True)


def revalidate_contact(club_slug, reason):
    revalidate_paths(["/kontakt"], reason=reason, club_slug=club_slug)


def revalidate_links(club_slug, reason):
    revalidate_paths(["/", "/kontakt", "/o-klube"], reason=reason, club_slug=club_slug)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def club_info_overview(request):
    club, error_response = get_editor_club_or_response(request.user)

    if error_response:
        return error_response

    contact = ContactInfo.objects.filter(club=club).first()
    documents = ClubDocument.objects.filter(club=club).order_by("order", "title")
    links = ClubLink.objects.filter(club=club).order_by("order", "title")

    return Response(
        {
            "club": {
                "id": club.id,
                "name": club.name,
                "slug": club.slug,
                "short_name": getattr(club, "short_name", ""),
            },
            "contact": AdminContactInfoSerializer(contact, context={"request": request}).data
            if contact
            else None,
            "documents": AdminClubDocumentSerializer(
                documents,
                many=True,
                context={"request": request},
            ).data,
            "links": AdminClubLinkSerializer(
                links,
                many=True,
                context={"request": request},
            ).data,
        }
    )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def admin_contact_detail(request):
    club, error_response = get_editor_club_or_response(request.user)

    if error_response:
        return error_response

    if not user_has_club_role(request.user, club, EDITOR_ROLES):
        return Response(
            {"detail": "Nemáš oprávnenie upravovať kontaktné informácie tohto klubu."},
            status=status.HTTP_403_FORBIDDEN,
        )

    contact = ContactInfo.objects.filter(club=club).first()

    if request.method == "GET":
        if not contact:
            return Response(None, status=status.HTTP_200_OK)

        serializer = AdminContactInfoSerializer(contact, context={"request": request})
        return Response(serializer.data)

    if contact:
        serializer = AdminContactInfoSerializer(
            contact,
            data=request.data,
            partial=request.method == "PATCH",
            context={"request": request},
        )
    else:
        serializer = AdminContactInfoSerializer(
            data=request.data,
            context={"request": request},
        )

    serializer.is_valid(raise_exception=True)
    serializer.save(club=club)

    revalidate_contact(club.slug, reason="ContactInfo saved in admin API")

    return Response(serializer.data, status=status.HTTP_200_OK)


class AdminClubDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = AdminClubDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        allowed_club_ids = get_allowed_club_ids(self.request.user)

        return (
            ClubDocument.objects.select_related("club")
            .filter(club_id__in=allowed_club_ids)
            .order_by("order", "title")
        )

    def perform_create(self, serializer):
        club, error_response = get_editor_club_or_response(self.request.user)

        if error_response:
            raise PermissionError("Nemáš oprávnenie spravovať klubové dokumenty.")

        serializer.save(club=club)
        revalidate_contact(club.slug, reason="ClubDocument created in admin API")

    def perform_update(self, serializer):
        obj = self.get_object()

        if not user_has_club_role(self.request.user, obj.club, EDITOR_ROLES):
            raise PermissionError("Nemáš oprávnenie upravovať tento dokument.")

        serializer.save()
        revalidate_contact(obj.club.slug, reason="ClubDocument updated in admin API")

    def perform_destroy(self, instance):
        club_slug = instance.club.slug

        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionError("Nemáš oprávnenie zmazať tento dokument.")

        instance.delete()
        revalidate_contact(club_slug, reason="ClubDocument deleted in admin API")


class AdminClubLinkViewSet(viewsets.ModelViewSet):
    serializer_class = AdminClubLinkSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        allowed_club_ids = get_allowed_club_ids(self.request.user)

        return (
            ClubLink.objects.select_related("club")
            .filter(club_id__in=allowed_club_ids)
            .order_by("order", "title")
        )

    def perform_create(self, serializer):
        club, error_response = get_editor_club_or_response(self.request.user)

        if error_response:
            raise PermissionError("Nemáš oprávnenie spravovať klubové odkazy.")

        serializer.save(club=club)
        revalidate_links(club.slug, reason="ClubLink created in admin API")

    def perform_update(self, serializer):
        obj = self.get_object()

        if not user_has_club_role(self.request.user, obj.club, EDITOR_ROLES):
            raise PermissionError("Nemáš oprávnenie upravovať tento odkaz.")

        serializer.save()
        revalidate_links(obj.club.slug, reason="ClubLink updated in admin API")

    def perform_destroy(self, instance):
        club_slug = instance.club.slug

        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionError("Nemáš oprávnenie zmazať tento odkaz.")

        instance.delete()
        revalidate_links(club_slug, reason="ClubLink deleted in admin API")