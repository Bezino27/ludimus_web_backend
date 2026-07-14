from rest_framework.routers import DefaultRouter

from .admin_views import (
    AdminCategoryLinkViewSet,
    AdminCategoryTrainingViewSet,
    AdminCategoryViewSet,
    AdminClubSeasonViewSet,
    AdminTrainingLocationViewSet,
)

router = DefaultRouter()
router.register("categories", AdminCategoryViewSet, basename="admin-team-categories")
router.register("club-seasons", AdminClubSeasonViewSet, basename="admin-club-seasons")
router.register("training-locations", AdminTrainingLocationViewSet, basename="admin-training-locations")
router.register("category-trainings", AdminCategoryTrainingViewSet, basename="admin-category-trainings")
router.register("category-links", AdminCategoryLinkViewSet, basename="admin-category-links")

urlpatterns = router.urls
