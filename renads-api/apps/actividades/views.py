"""ViewSets del módulo Actividades. Vistas delgadas: services/selectors."""

from django.contrib.contenttypes.models import ContentType
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsInstitutionalMember
from apps.common.selectors import usuario_pertenece_a_entidad
from apps.convenios.models import Ipress, University
from apps.convenios.permissions import exigir_roles
from apps.convenios.views import _catalog_viewset
from apps.actividades import models as am
from apps.actividades import selectors, services
from apps.actividades.filters import TeachingActivityFilter
from apps.actividades.permissions import ActivityScope
from apps.actividades.serializers import (
    ActivityStatusHistorySerializer,
    ActivityValidationInputSerializer,
    CambiarEstadoActividadSerializer,
    SubsanarSerializer,
    TeachingActivityReadSerializer,
    TeachingActivityUpdateSerializer,
    TeachingActivityWriteSerializer,
)


class TeachingActivityViewSet(viewsets.ModelViewSet):
    """CRUD de actividades docente-asistenciales y acciones de validación."""

    permission_classes = [IsAuthenticated, IsInstitutionalMember, ActivityScope]
    filterset_class = TeachingActivityFilter
    search_fields = ["descripcion"]
    ordering_fields = ["fecha_actividad", "id"]
    ordering = ["-id"]

    def get_queryset(self):
        return selectors.actividades_visibles(self.request.user)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return TeachingActivityReadSerializer
        if self.action in ("update", "partial_update"):
            return TeachingActivityUpdateSerializer
        return TeachingActivityWriteSerializer

    def _read(self, actividad) -> Response:
        return Response(TeachingActivityReadSerializer(actividad).data)

    def _verificar_ambito(self, interno, ipress):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name="Administrador RENADS").exists():
            return
        ct_uni = ContentType.objects.get_for_model(University).id
        ct_ip = ContentType.objects.get_for_model(Ipress).id
        if not (
            usuario_pertenece_a_entidad(user, ct_uni, interno.universidad_id)
            or usuario_pertenece_a_entidad(user, ct_ip, ipress.id)
        ):
            raise PermissionDenied("La actividad está fuera de tu ámbito institucional.")

    def create(self, request, *args, **kwargs):
        exigir_roles(request, "Universidad", "Tutor", "Sede docente")
        ser = TeachingActivityWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        self._verificar_ambito(ser.validated_data["interno"], ser.validated_data["ipress"])
        actividad = services.registrar_actividad(datos=ser.validated_data, usuario=request.user)
        return Response(TeachingActivityReadSerializer(actividad).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        actividad = self.get_object()
        ser = TeachingActivityUpdateSerializer(actividad, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        actividad = services.actualizar_actividad(
            actividad=actividad, datos=ser.validated_data, usuario=request.user
        )
        return self._read(actividad)

    @action(detail=True, methods=["post"], url_path="validar")
    def validar(self, request, pk=None):
        actividad = self.get_object()
        exigir_roles(request, "Tutor")
        ser = ActivityValidationInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.validar_actividad(actividad=actividad, datos=ser.validated_data, usuario=request.user)
        return self._read(actividad)

    @action(detail=True, methods=["post"], url_path="subsanar")
    def subsanar(self, request, pk=None):
        actividad = self.get_object()
        exigir_roles(request, "Universidad", "Tutor", "Sede docente")
        ser = SubsanarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.subsanar_actividad(actividad=actividad, datos=ser.validated_data, usuario=request.user)
        return self._read(actividad)

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        actividad = self.get_object()
        exigir_roles(request, "Administrador RENADS")
        ser = CambiarEstadoActividadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.cambiar_estado_actividad(
            actividad=actividad,
            nuevo_estado_codigo=ser.validated_data["estado_codigo"],
            usuario=request.user,
            observacion=ser.validated_data.get("observacion", ""),
        )
        return self._read(actividad)

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        actividad = self.get_object()
        return Response(
            ActivityStatusHistorySerializer(selectors.historial_actividad(actividad), many=True).data
        )


# Catálogos (solo lectura)
CATALOG_VIEWSETS = {
    "activity-types": _catalog_viewset(am.ActivityType),
    "activity-statuses": _catalog_viewset(am.ActivityStatus),
}
