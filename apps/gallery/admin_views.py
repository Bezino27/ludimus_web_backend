from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import GalleryAlbum, GalleryImage
from .admin_serializers import AdminGalleryAlbumSerializer, AdminGalleryImageSerializer
from apps.clubs.models import ClubMembership
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminGalleryAlbumViewSet(viewsets.ModelViewSet):
    serializer_class = AdminGalleryAlbumSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = (
            GalleryAlbum.objects.filter(club_id__in=club_ids)
            .select_related("club")
            .prefetch_related("images")
            .order_by("-created_at")
        )

        club_slug = self.request.query_params.get("club")
        is_published = self.request.query_params.get("is_published")

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        if is_published is not None:
            if is_published.lower() == "true":
                queryset = queryset.filter(is_published=True)
            elif is_published.lower() == "false":
                queryset = queryset.filter(is_published=False)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data["club"]
        if not user_has_club_role(self.request.user, club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie vytvárať albumy pre tento klub.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať tento album.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie zmazať tento album.")
        instance.delete()


class AdminGalleryImageViewSet(viewsets.ModelViewSet):
    serializer_class = AdminGalleryImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = (
            GalleryImage.objects.filter(album__club_id__in=club_ids)
            .select_related("album", "album__club")
            .order_by("order", "id")
        )

        album_id = self.request.query_params.get("album")
        club_slug = self.request.query_params.get("club")

        if album_id:
            queryset = queryset.filter(album_id=album_id)

        if club_slug:
            queryset = queryset.filter(album__club__slug=club_slug)

        return queryset

    def perform_create(self, serializer):
        album = serializer.validated_data["album"]
        if not user_has_club_role(self.request.user, album.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie pridávať obrázky do tohto albumu.")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if not user_has_club_role(self.request.user, instance.album.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať tento obrázok.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_club_role(self.request.user, instance.album.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie zmazať tento obrázok.")
        instance.delete()