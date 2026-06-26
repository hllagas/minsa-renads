"""Router del módulo Convenios (núcleo + catálogos + entidades)."""

from rest_framework.routers import DefaultRouter

from apps.convenios import views

router = DefaultRouter()

# Núcleo
router.register("conventions", views.ConventionViewSet, basename="convention")
router.register("convention-templates", views.ConventionTemplateViewSet)
router.register("representatives", views.RepresentativeViewSet)
router.register("ubigeos", views.UbigeoViewSet)

# Catálogos (solo lectura)
for basename, viewset in views.CATALOG_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

# Entidades (CRUD)
for basename, viewset in views.ENTITY_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

urlpatterns = router.urls
