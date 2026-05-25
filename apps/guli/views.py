import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.throttling import ScopedRateThrottle

from .models import RecruitmentForm
from .serializers import RecruitmentFormSerializer

logger = logging.getLogger(__name__)


class RecruitmentFormCreateView(generics.CreateAPIView):
    queryset = RecruitmentForm.objects.all()
    serializer_class = RecruitmentFormSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "recruitment_form"

    def perform_create(self, serializer):
        form = serializer.save()

        try:
            send_mail(
                subject="Nový záujemca o tréning",
                message=(
                    f"Prišiel nový náborový formulár.\n\n"
                    f"Meno dieťaťa: {form.child_full_name}\n"
                    f"Rok narodenia: {form.birth_year}\n"
                    f"Email: {form.email}\n"
                    f"Telefón: {form.phone or '-'}\n"
                    f"Poznámka: {form.note or '-'}\n"
                    f"Odoslané: {form.created_at}\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["guli@ludimus.sk"],
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Nepodarilo sa odoslať email pre náborový formulár id=%s.",
                form.id,
            )


class RecruitmentFormListView(generics.ListAPIView):
    queryset = RecruitmentForm.objects.all()
    serializer_class = RecruitmentFormSerializer
    permission_classes = [IsAdminUser]


class RecruitmentFormDetailView(generics.RetrieveAPIView):
    queryset = RecruitmentForm.objects.all()
    serializer_class = RecruitmentFormSerializer
    lookup_field = "id"
    permission_classes = [IsAdminUser]
