from rest_framework import generics
from .models import Post
from .serializers import PostListSerializer, PostDetailSerializer


class ClubPostListView(generics.ListAPIView):
    serializer_class = PostListSerializer

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]
        return (
            Post.objects.filter(
                club__slug=club_slug,
                club__is_active=True,
                status="published",
            )
            .select_related("club", "category", "author")
            .order_by("-published_at", "-created_at")
        )


class ClubPostDetailView(generics.RetrieveAPIView):
    serializer_class = PostDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]
        return (
            Post.objects.filter(
                club__slug=club_slug,
                club__is_active=True,
                status="published",
            )
            .select_related("club", "category", "author")
        )