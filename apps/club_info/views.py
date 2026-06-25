from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import ContactInfo, ClubDocument
from .serializers import ContactInfoSerializer, ClubDocumentSerializer


@api_view(["GET"])
def public_contact_detail(request, club_slug):
    try:
        contact = ContactInfo.objects.select_related("club").get(
            club__slug=club_slug,
            club__is_active=True,
            is_active=True,
        )
    except ContactInfo.DoesNotExist:
        return Response(
            {"detail": "Kontaktné informácie pre tento klub neboli nájdené."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ContactInfoSerializer(contact, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
def public_documents_list(request, club_slug):
    documents = (
        ClubDocument.objects.select_related("club")
        .filter(
            club__slug=club_slug,
            club__is_active=True,
            is_active=True,
        )
        .order_by("order", "title")
    )

    serializer = ClubDocumentSerializer(
        documents,
        many=True,
        context={"request": request},
    )

    return Response(serializer.data)
