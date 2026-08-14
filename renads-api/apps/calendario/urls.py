"""Rutas de la feature Calendario: CRUD de actividades de calendario."""

from rest_framework.routers import DefaultRouter

from apps.calendario.views import CalendarActivityViewSet

router = DefaultRouter()
router.register(
    "calendar-activities", CalendarActivityViewSet, basename="calendar-activity"
)

urlpatterns = router.urls
