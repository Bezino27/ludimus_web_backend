from rest_framework import generics
from .models import Partner
from .serializers import PartnerSerializer


class ClubPartnerListView(generics.ListAPIView):
    serializer_class = PartnerSerializer

    def get_queryset(self):
        club_slug = self.kwargs["club_slug"]

        return (
            Partner.objects.filter(
                club__slug=club_slug,
                club__is_active=True,
                is_active=True,
            )
            .select_related("club")
            .order_by("order", "name")
        )