"""Rutas de administración transversal: usuarios, grupos (roles), permisos y el
lookup de tipos de entidad asignables a perfiles."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.common.views import (
    AssignableEntityTypeView,
    ContentTypeViewSet,
    GroupViewSet,
    PermissionViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("groups", GroupViewSet, basename="group")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("content-types", ContentTypeViewSet, basename="content-type")

urlpatterns = [
    path(
        "profile-entity-types/",
        AssignableEntityTypeView.as_view(),
        name="profile-entity-types",
    ),
    *router.urls,
]
