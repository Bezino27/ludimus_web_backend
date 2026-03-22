from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Post
from .admin_serializers import AdminPostSerializer
from apps.clubs.models import ClubMembership
from apps.common.permissions import user_has_club_role, EDITOR_ROLES
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.exceptions import PermissionDenied

from django.core.files.storage import default_storage
from .models import Post
from apps.clubs.models import Club
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


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

        queryset = Post.objects.filter(
            club_id__in=club_ids
        ).select_related("club", "category", "author").order_by("-created_at")

        club_slug = self.request.query_params.get("club")
        status_value = self.request.query_params.get("status")

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset

    def perform_create(self, serializer):
        club = serializer.validated_data["club"]
        if not user_has_club_role(self.request.user, club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie vytvárať články pre tento klub.")
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie upravovať tento článok.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_club_role(self.request.user, instance.club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie zmazať tento článok.")
        instance.delete()



class AdminPostImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        club_id = request.data.get("club")
        image = request.FILES.get("image")

        if not club_id:
            return Response({"detail": "Chýba club."}, status=status.HTTP_400_BAD_REQUEST)

        if not image:
            return Response({"detail": "Chýba image."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"detail": "Klub neexistuje."}, status=status.HTTP_404_NOT_FOUND)

        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            raise PermissionDenied("Nemáš oprávnenie pre tento klub.")

        file_path = default_storage.save(f"posts/content/{image.name}", image)
        file_url = request.build_absolute_uri(default_storage.url(file_path))

        return Response({
            "url": file_url
        })
    

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from django.core.files.storage import default_storage

from .models import PostCategory
from .admin_serializers import AdminPostCategorySerializer
from apps.clubs.models import Club
from apps.common.permissions import user_has_club_role, EDITOR_ROLES


class AdminPostCategoryListView(APIView):
    def get(self, request):
        club_slug = request.query_params.get("club")

        queryset = PostCategory.objects.select_related("club").all().order_by("name")

        if club_slug:
            queryset = queryset.filter(club__slug=club_slug)

        if club_slug:
            club = Club.objects.filter(slug=club_slug).first()
            if club and not user_has_club_role(request.user, club, EDITOR_ROLES):
                return Response({"detail": "Nemáš oprávnenie pre tento klub."}, status=403)

        serializer = AdminPostCategorySerializer(queryset, many=True)
        return Response(serializer.data)


class AdminPostFeaturedImageUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        club_id = request.data.get("club")
        image = request.FILES.get("image")

        if not club_id:
            return Response({"detail": "Chýba club."}, status=status.HTTP_400_BAD_REQUEST)

        if not image:
            return Response({"detail": "Chýba image."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({"detail": "Klub neexistuje."}, status=status.HTTP_404_NOT_FOUND)

        if not user_has_club_role(request.user, club, EDITOR_ROLES):
            return Response({"detail": "Nemáš oprávnenie pre tento klub."}, status=403)

        file_path = default_storage.save(f"posts/featured/{image.name}", image)
        file_url = request.build_absolute_uri(default_storage.url(file_path))

        return Response({
            "url": file_url,
            "path": file_path,
        })