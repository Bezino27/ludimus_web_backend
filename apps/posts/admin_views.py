from django.core.files.storage import default_storage

from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clubs.models import Club, ClubMembership
from apps.common.image_uploads import optimize_uploaded_image
from apps.common.permissions import EDITOR_ROLES, user_has_club_role

from .admin_serializers import (
    AdminPostCategorySerializer,
    AdminPostSerializer,
)
from .models import Post, PostCategory
from .revalidation import revalidate_post_paths


# # ADMIN POSTS
class AdminPostViewSet(viewsets.ModelViewSet):
    serializer_class = AdminPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        club_ids = ClubMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=EDITOR_ROLES,
        ).values_list("club_id", flat=True)

        queryset = (
            Post.objects.filter(club_id__in=club_ids)
            .select_related("club", "category", "author")
            .order_by("-created_at")
        )

        club_slug = self.request.query_params.get("club")
        status_value = self.request.query_params.get("status")

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data["club"]

        if not user_has_club_role(
            self.request.user,
            club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie vytvárať články pre tento klub."
            )

        post = serializer.save(author=self.request.user)

        revalidate_post_paths(
            post,
            reason="Post created via admin API",
        )

    def perform_update(self, serializer):
        instance = self.get_object()

        if not user_has_club_role(
            self.request.user,
            instance.club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie upravovať tento článok."
            )

        old_slug = instance.slug
        post = serializer.save()

        revalidate_post_paths(
            post,
            reason="Post updated via admin API",
            old_slug=old_slug,
        )

    def perform_destroy(self, instance):
        if not user_has_club_role(
            self.request.user,
            instance.club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie zmazať tento článok."
            )

        post = instance
        instance.delete()

        revalidate_post_paths(
            post,
            reason="Post deleted via admin API",
        )


# # ARTICLE CONTENT IMAGE UPLOAD
class AdminPostImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        club_id = request.data.get("club")
        image = request.FILES.get("image")

        if not club_id:
            return Response(
                {"detail": "Chýba club."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not image:
            return Response(
                {"detail": "Chýba image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response(
                {"detail": "Klub neexistuje."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_has_club_role(
            request.user,
            club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie pre tento klub."
            )

        optimized_image = optimize_uploaded_image(
            image,
            "article",
            filename_prefix="post-content-image",
        )

        file_path = default_storage.save(
            f"posts/content/{optimized_image.name}",
            optimized_image,
        )

        file_url = request.build_absolute_uri(
            default_storage.url(file_path)
        )

        return Response({
            "url": file_url,
        })


# # ARTICLE CATEGORIES
class AdminPostCategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        club_slug = request.query_params.get("club")

        queryset = (
            PostCategory.objects
            .select_related("club")
            .all()
            .order_by("name")
        )

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

            club = Club.objects.filter(slug=club_slug).first()

            if club and not user_has_club_role(
                request.user,
                club,
                EDITOR_ROLES,
            ):
                raise PermissionDenied(
                    "Nemáš oprávnenie pre tento klub."
                )

        serializer = AdminPostCategorySerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)


# # FEATURED IMAGE UPLOAD
class AdminPostFeaturedImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        club_id = request.data.get("club")
        image = request.FILES.get("image")

        if not club_id:
            return Response(
                {"detail": "Chýba club."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not image:
            return Response(
                {"detail": "Chýba image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response(
                {"detail": "Klub neexistuje."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user_has_club_role(
            request.user,
            club,
            EDITOR_ROLES,
        ):
            raise PermissionDenied(
                "Nemáš oprávnenie pre tento klub."
            )

        optimized_image = optimize_uploaded_image(
            image,
            "article",
            filename_prefix="post-featured-image",
        )

        file_path = default_storage.save(
            f"posts/featured/{optimized_image.name}",
            optimized_image,
        )

        file_url = request.build_absolute_uri(
            default_storage.url(file_path)
        )

        return Response({
            "url": file_url,
            "path": file_path,
        })