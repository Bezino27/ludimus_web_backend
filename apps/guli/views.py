from django.core.mail import send_mail
from rest_framework import generics
from .models import RecruitmentForm
from .serializers import RecruitmentFormSerializer


class RecruitmentFormCreateView(generics.CreateAPIView):
    queryset = RecruitmentForm.objects.all()
    serializer_class = RecruitmentFormSerializer

    def perform_create(self, serializer):
        form = serializer.save()

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
            from_email="guli@ludimus.sk",
            recipient_list=["guli@ludimus.sk"],
            fail_silently=False,
        )


class RecruitmentFormListView(generics.ListAPIView):
    queryset = RecruitmentForm.objects.all()
    serializer_class = RecruitmentFormSerializer


class RecruitmentFormDetailView(generics.RetrieveAPIView):
    queryset = RecruitmentForm.objects.all()
    serializer_class = RecruitmentFormSerializer
    lookup_field = "id"