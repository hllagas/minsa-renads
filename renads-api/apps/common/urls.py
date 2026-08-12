"""Rutas de administración transversal: usuarios, grupos (roles), permisos y el
lookup de tipos de entidad asignables a perfiles."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.common.views import (
    AssignableEntityTypeView,
    GroupViewSet,
    PermissionViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("groups", GroupViewSet, basename="group")
router.register("permissions", PermissionViewSet, basename="permission")

urlpatterns = [
    path(
        "profile-entity-types/",
        AssignableEntityTypeView.as_view(),
        name="profile-entity-types",
    ),
    *router.urls,
]
