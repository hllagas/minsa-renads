"""Router del módulo Internados (bloque núcleo)."""

from rest_framework.routers import DefaultRouter

from apps.internados import views

router = DefaultRouter()
router.register("interns", views.InternshipViewSet, basename="intern")
router.register("rotations", views.RotationViewSet, basename="rotation")
router.register("students", views.StudentViewSet, basename="student")
router.register("tutors", views.TutorViewSet, basename="tutor")

# Catálogos (solo lectura)
for basename, viewset in views.CATALOG_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

# Catálogos maestros con CRUD (academic-periods, annex-documents)
for basename, viewset in views.ENTITY_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

urlpatterns = router.urls
