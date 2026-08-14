"""ViewSet de la feature Calendario. Vista delgada: escritura vía services."""

from rest_framework.permissions import IsAuthenticated

from apps.calendario.filters import CalendarActivityFilter
from apps.calendario.models import CalendarActivity
from apps.calendario import services
from apps.calendario.serializers import (
    CalendarActivityReadSerializer,
    CalendarActivityWriteSerializer,
)
from apps.convenios.permissions import IsAdminRoleOrReadOnly
from apps.convenios.views import AuditedModelViewSet


class CalendarActivityViewSet(AuditedModelViewSet):
    """CRUD de actividades de calendario.

    Escritura solo superusuario / `Administrador RENADS` (`IsAdminRoleOrReadOnly`);
    lectura para autenticados. La escritura delega en los services, que fijan
    `creado_por`/`actualizado_por` y registran la auditoría; por eso se
    sobrescriben `perform_create`/`perform_update` evitando la doble auditoría de
    `AuditedModelViewSet`. Este viewset **no** se gatea con `IsModuleEnabled`
    (el propio calendario no está sujeto a ventanas).
    """

    queryset = CalendarActivity.objects.prefetch_related("content_types").all()
    permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]
    filterset_class = CalendarActivityFilter
    search_fields = ["nombre", "detalle"]
    ordering_fields = ["numero_orden", "fecha_inicio", "fecha_fin", "id"]
    ordering = ["numero_orden", "id"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return CalendarActivityReadSerializer
        return CalendarActivityWriteSerializer

    def perform_create(self, serializer):
        serializer.instance = services.crear_actividad_calendario(
            datos=serializer.validated_data, usuario=self.request.user
        )

    def perform_update(self, serializer):
        serializer.instance = services.actualizar_actividad_calendario(
            actividad=serializer.instance,
            datos=serializer.validated_data,
            usuario=self.request.user,
        )
