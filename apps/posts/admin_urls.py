from django.urls import path
from rest_framework.routers import DefaultRouter
from .admin_views import (
    AdminPostViewSet,
    AdminPostImageUploadView,
    AdminPostFeaturedImageUploadView,
    AdminPostCategoryListView,
)

router = DefaultRouter()
router.register("", AdminPostViewSet, basename="admin-posts")

urlpatterns = [
    path("upload/image/", AdminPostImageUploadView.as_view(), name="admin-post-image-upload"),
    path("upload/featured-image/", AdminPostFeaturedImageUploadView.as_view(), name="admin-post-featured-image-upload"),
    path("categories/", AdminPostCategoryListView.as_view(), name="admin-post-categories"),
] + router.urls