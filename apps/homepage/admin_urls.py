from rest_framework.routers import DefaultRouter
from .admin_views import AdminHomepageSectionViewSet

router = DefaultRouter()
router.register("", AdminHomepageSectionViewSet, basename="admin-homepage")

urlpatterns = router.urls