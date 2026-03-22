from rest_framework.routers import DefaultRouter
from .admin_views import AdminGalleryAlbumViewSet, AdminGalleryImageViewSet

router = DefaultRouter()
router.register("albums", AdminGalleryAlbumViewSet, basename="admin-gallery-albums")
router.register("images", AdminGalleryImageViewSet, basename="admin-gallery-images")

urlpatterns = router.urls