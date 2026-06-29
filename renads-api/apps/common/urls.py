"""Rutas de administración transversal: usuarios, grupos (roles) y permisos."""

from rest_framework.routers import DefaultRouter

from apps.common.views import GroupViewSet, PermissionViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("groups", GroupViewSet, basename="group")
router.register("permissions", PermissionViewSet, basename="permission")

urlpatterns = router.urls
