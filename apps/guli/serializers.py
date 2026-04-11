import re
from datetime import datetime

from rest_framework import serializers
from .models import RecruitmentForm


class RecruitmentFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruitmentForm
        fields = [
            "id",
            "child_full_name",
            "birth_year",
            "email",
            "phone",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_child_full_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Meno a priezvisko dieťaťa je povinné.")
        return value.strip()

    def validate_birth_year(self, value):
        current_year = datetime.now().year

        if value < 2005 or value > current_year:
            raise serializers.ValidationError("Zadaj platný rok narodenia.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()

        if not value:
            raise serializers.ValidationError("Email je povinný.")

        # DRF EmailField už kontroluje základný formát,
        # tu len pridávame pár vlastných pravidiel
        if ".." in value:
            raise serializers.ValidationError("Zadaj platný email.")

        return value

    def validate_phone(self, value):
        if value in [None, ""]:
            return ""

        value = value.strip().replace(" ", "")

        # Príklad povoleného formátu: +421900123456
        if not re.fullmatch(r"^\+421\d{9}$", value):
            raise serializers.ValidationError(
                "Telefón musí byť vo formáte +421900123456."
            )

        return value