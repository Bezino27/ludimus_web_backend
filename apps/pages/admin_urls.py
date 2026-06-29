from rest_framework.routers import DefaultRouter

from .admin_views import (
    AdminPageSectionContactItemViewSet,
    AdminPageSectionViewSet,
    AdminPageViewSet,
)

router = DefaultRouter()
router.register("sections", AdminPageSectionViewSet, basename="admin-page-sections")
router.register(
    "section-contact-items",
    AdminPageSectionContactItemViewSet,
    basename="admin-page-section-contact-items",
)
router.register("", AdminPageViewSet, basename="admin-pages")

urlpatterns = router.urls