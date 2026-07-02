from rest_framework.routers import DefaultRouter

from .admin_views import AdminCategoryViewSet, AdminClubSeasonViewSet

router = DefaultRouter()
router.register("categories", AdminCategoryViewSet, basename="admin-team-categories")
router.register("club-seasons", AdminClubSeasonViewSet, basename="admin-club-seasons")

urlpatterns = router.urls