from rest_framework.routers import DefaultRouter
from .admin_views import AdminPartnerViewSet

router = DefaultRouter()
router.register("", AdminPartnerViewSet, basename="admin-partners")

urlpatterns = router.urls