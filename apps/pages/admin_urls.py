from rest_framework.routers import DefaultRouter

from .admin_views import (
    AdminPageSectionContactItemViewSet,
    AdminPageSectionItemViewSet,
    AdminPageSectionViewSet,
    AdminPageViewSet,
)

router = DefaultRouter()
router.register("sections", AdminPageSectionViewSet, basename="admin-page-sections")
router.register(
    "section-items",
    AdminPageSectionItemViewSet,
    basename="admin-page-section-items",
)
router.register(
    "section-contact-items",
    AdminPageSectionContactItemViewSet,
    basename="admin-page-section-contact-items",
)
router.register("", AdminPageViewSet, basename="admin-pages")

urlpatterns = router.urls