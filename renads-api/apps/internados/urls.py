"""Router del módulo Internados (bloque núcleo)."""

from rest_framework.routers import DefaultRouter

from apps.internados import views

router = DefaultRouter()
router.register("internships", views.InternshipViewSet, basename="internship")
router.register("rotations", views.RotationViewSet, basename="rotation")
router.register("interns", views.InternViewSet, basename="intern")
router.register("tutors", views.TutorViewSet, basename="tutor")

# Catálogos (solo lectura)
for basename, viewset in views.CATALOG_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

urlpatterns = router.urls
