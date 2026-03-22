from rest_framework.routers import DefaultRouter
from .admin_views import AdminPageViewSet

router = DefaultRouter()
router.register("", AdminPageViewSet, basename="admin-pages")

urlpatterns = router.urls