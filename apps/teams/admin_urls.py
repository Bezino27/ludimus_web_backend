from rest_framework.routers import DefaultRouter

from .admin_views import AdminCategoryViewSet

router = DefaultRouter()
router.register("categories", AdminCategoryViewSet, basename="admin-team-categories")

urlpatterns = router.urls
