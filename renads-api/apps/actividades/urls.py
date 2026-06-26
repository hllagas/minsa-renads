"""Router del módulo Actividades."""

from rest_framework.routers import DefaultRouter

from apps.actividades import views

router = DefaultRouter()
router.register("teaching-activities", views.TeachingActivityViewSet, basename="teaching-activity")

for basename, viewset in views.CATALOG_VIEWSETS.items():
    router.register(basename, viewset, basename=basename)

urlpatterns = router.urls
