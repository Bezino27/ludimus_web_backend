from rest_framework import generics
from .models import Club
from .serializers import ClubSerializer


class ClubDetailBySlugView(generics.RetrieveAPIView):
    queryset = Club.objects.filter(is_active=True)
    serializer_class = ClubSerializer
    lookup_field = "slug"