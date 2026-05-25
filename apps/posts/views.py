from rest_framework import generics
from .models import Post
from .serializers import PostListSerializer, PostDetailSerializer


class ClubPostListView(generics.ListAPIView):
    serializer_class = PostListSerializer

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]
        queryset = (
            Post.objects.filter(
                club__slug=club_slug,
                club__is_active=True,
                status="published",
            )
            .select_related("club", "category", "author")
            .order_by("-published_at", "-created_at")
        )

        limit = self.request.query_params.get("limit")

        if limit:
            try:
                limit_value = min(max(int(limit), 1), 50)
            except ValueError:
                limit_value = 50

            return queryset[:limit_value]

        return queryset


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
