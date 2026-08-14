"""Router del módulo Convenios (núcleo + catálogos + entidades)."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.convenios import views

router = DefaultRouter()

# Núcleo
router.register("conventions", views.ConventionViewSet, basename="convention")
router.register("convention-templates", views.ConventionTemplateViewSet)
router.register(
    "clinical-field-registrations",
    views.ClinicalFieldRegistrationViewSet,
    basename="clinical-field-registration",
)
router.register(
    "clinical-field-allocations",
    views.ClinicalFieldAllocationViewSet,
    basename="clinical-field-allocation",
)
router.register("representatives", views.RepresentativeViewSet)
router.register("ubigeos", views.UbigeoViewSet)
router.register("documents", views.DocumentViewSet, basename="document")
router.register("audit-logs", views.AuditLogViewSet, basename="audit-log")

# Catálogos (solo lectura)
for basename, viewset in views.CATALOG_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

# Entidades (CRUD)
for basename, viewset in views.ENTITY_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

urlpatterns = [
    path(
        "solicitante-content-types/",
        views.SolicitanteContentTypeView.as_view(),
        name="solicitante-content-types",
    ),
    *router.urls,
]
