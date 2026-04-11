from django.urls import path
from .views import (
    RecruitmentFormCreateView,
    RecruitmentFormListView,
    RecruitmentFormDetailView,
)

urlpatterns = [
    path("recruitment-forms/", RecruitmentFormListView.as_view(), name="recruitment-form-list"),
    path("recruitment-forms/create/", RecruitmentFormCreateView.as_view(), name="recruitment-form-create"),
    path("recruitment-forms/<int:id>/", RecruitmentFormDetailView.as_view(), name="recruitment-form-detail"),
]