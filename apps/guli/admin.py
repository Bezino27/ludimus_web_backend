from django.contrib import admin
from .models import RecruitmentForm


@admin.register(RecruitmentForm)
class RecruitmentFormAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "child_full_name",
        "birth_year",
        "email",
        "phone",
        "created_at",
    )
    search_fields = ("child_full_name", "email", "phone")
    list_filter = ("birth_year", "created_at")
    ordering = ("-created_at",)