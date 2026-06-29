from rest_framework.routers import DefaultRouter

from .admin_views import AdminPollViewSet

router = DefaultRouter()
router.register("", AdminPollViewSet, basename="admin-polls")

urlpatterns = router.urls
