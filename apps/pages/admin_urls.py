from rest_framework.routers import DefaultRouter

from .admin_views import AdminPageSectionViewSet, AdminPageViewSet

router = DefaultRouter()
router.register("sections", AdminPageSectionViewSet, basename="admin-page-sections")
router.register("", AdminPageViewSet, basename="admin-pages")

urlpatterns = router.urls