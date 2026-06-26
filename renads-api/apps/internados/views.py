"""ViewSets del módulo Internados (bloque núcleo). Vistas delgadas: services/selectors."""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.contenttypes.models import ContentType

from apps.common.permissions import IsInstitutionalMember, exigir_ambito
from apps.common.services import registrar_auditoria
from apps.convenios.models import University
from apps.convenios.permissions import exigir_roles
from apps.convenios.views import AuditedModelViewSet, _catalog_viewset
from apps.internados import models as im
from apps.internados import selectors, services
from apps.internados.filters import InternshipFilter, RotationFilter
from apps.internados.models import Rotation
from apps.internados.permissions import InternshipScope, IsUniversityOrReadOnly
from apps.internados.serializers import InternSerializer, TutorSerializer
from apps.internados.serializers import (
    CambiarEstadoInternadoSerializer,
    CambiarEstadoRotacionSerializer,
    CambiarTutorSerializer,
    InternshipReadSerializer,
    InternshipStatusHistorySerializer,
    InternshipUpdateSerializer,
    InternshipWriteSerializer,
    RotationAuthorizationSerializer,
    RotationReadSerializer,
    RotationStatusHistorySerializer,
    RotationWriteSerializer,
)


class InternshipViewSet(viewsets.ModelViewSet):
    """CRUD de internados y acciones de flujo. Escritura vía services; lectura vía selectors."""

    permission_classes = [IsAuthenticated, IsInstitutionalMember, InternshipScope]
    filterset_class = InternshipFilter
    search_fields = ["interno__numero_documento", "interno__nombres", "interno__apellido_paterno"]
    ordering_fields = ["fecha_inicio", "fecha_fin", "id"]
    ordering = ["-id"]

    def get_queryset(self):
        return selectors.internados_visibles(self.request.user)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return InternshipReadSerializer
        return InternshipWriteSerializer

    def _read(self, internado) -> Response:
        return Response(InternshipReadSerializer(internado).data)

    def create(self, request, *args, **kwargs):
        exigir_roles(request, "Universidad")
        ser = InternshipWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        interno = ser.validated_data["interno"]
        ct_uni = ContentType.objects.get_for_model(University).id
        exigir_ambito(request.user, ct_uni, interno.universidad_id)
        internado = services.crear_internado(datos=ser.validated_data, usuario=request.user)
        return Response(InternshipReadSerializer(internado).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        internado = self.get_object()
        ser = InternshipUpdateSerializer(internado, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        internado = services.actualizar_internado(
            internado=internado, datos=ser.validated_data, usuario=request.user
        )
        return self._read(internado)

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        internado = self.get_object()
        exigir_roles(request, "Administrador RENADS")
        ser = CambiarEstadoInternadoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        internado = services.cambiar_estado_internado(
            internado=internado,
            nuevo_estado_codigo=ser.validated_data["estado_codigo"],
            usuario=request.user,
            observacion=ser.validated_data.get("observacion", ""),
        )
        return self._read(internado)

    @action(detail=True, methods=["post"], url_path="cambiar-tutor")
    def cambiar_tutor(self, request, pk=None):
        internado = self.get_object()
        exigir_roles(request, "Universidad")
        ser = CambiarTutorSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        internado = services.cambiar_tutor(
            internado=internado, datos=ser.validated_data, usuario=request.user
        )
        return self._read(internado)

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        internado = self.get_object()
        return Response(
            InternshipStatusHistorySerializer(selectors.historial_internado(internado), many=True).data
        )

    @action(detail=True, methods=["get", "post"], url_path="rotaciones")
    def rotaciones(self, request, pk=None):
        internado = self.get_object()
        if request.method == "POST":
            exigir_roles(request, "Universidad")
            ser = RotationWriteSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            services.crear_rotacion(internado=internado, datos=ser.validated_data, usuario=request.user)
        qs = selectors.rotaciones_de(internado)
        return Response(RotationReadSerializer(qs, many=True).data)


class RotationViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura de rotaciones y acciones de autorización/inicio/estado."""

    permission_classes = [IsAuthenticated, IsInstitutionalMember, InternshipScope]
    filterset_class = RotationFilter
    ordering_fields = ["numero_rotacion", "fecha_inicio", "id"]
    ordering = ["-id"]
    serializer_class = RotationReadSerializer

    def get_queryset(self):
        internados = selectors.internados_visibles(self.request.user)
        return Rotation.objects.filter(internado__in=internados).select_related(
            "ipress_origen", "ipress_destino", "servicio_area", "estado_actual"
        )

    def _read(self, rotacion) -> Response:
        return Response(RotationReadSerializer(rotacion).data)

    @action(detail=True, methods=["post"], url_path="autorizar")
    def autorizar(self, request, pk=None):
        rotacion = self.get_object()
        exigir_roles(request, "Autoridad de convenio")
        ser = RotationAuthorizationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.autorizar_rotacion(rotacion=rotacion, datos=ser.validated_data, usuario=request.user)
        return self._read(rotacion)

    @action(detail=True, methods=["post"], url_path="iniciar")
    def iniciar(self, request, pk=None):
        rotacion = self.get_object()
        exigir_roles(request, "Universidad")
        services.iniciar_rotacion(rotacion=rotacion, usuario=request.user)
        return self._read(rotacion)

    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        rotacion = self.get_object()
        exigir_roles(request, "Administrador RENADS")
        ser = CambiarEstadoRotacionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.cambiar_estado_rotacion(
            rotacion=rotacion,
            nuevo_estado_codigo=ser.validated_data["estado_codigo"],
            usuario=request.user,
            observacion=ser.validated_data.get("observacion", ""),
        )
        return self._read(rotacion)

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        rotacion = self.get_object()
        return Response(
            RotationStatusHistorySerializer(selectors.historial_rotacion(rotacion), many=True).data
        )


# ---------------------------------------------------------------------------
# Bloque 2 — Catálogos (solo lectura) y personas (Intern / Tutor)
# ---------------------------------------------------------------------------
class InternViewSet(AuditedModelViewSet):
    """CRUD de internos. Escritura por rol Universidad/Administrador; alcance por universidad."""

    serializer_class = InternSerializer
    permission_classes = [IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]
    filterset_fields = ["universidad", "carrera_profesional", "especialidad", "numero_documento", "activo"]
    search_fields = ["numero_documento", "nombres", "apellido_paterno"]
    ordering = ["id"]

    def get_queryset(self):
        return selectors.interns_visibles(self.request.user)

    def perform_create(self, serializer):
        objeto = serializer.save(creado_por=self.request.user)
        registrar_auditoria(self.request.user, "CREAR", objeto)

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ct_uni = ContentType.objects.get_for_model(University).id
        exigir_ambito(request.user, ct_uni, ser.validated_data["universidad"].id)
        self.perform_create(ser)
        return Response(ser.data, status=201)


class TutorViewSet(AuditedModelViewSet):
    """CRUD de tutores/docentes. Escritura por rol Universidad/Administrador."""

    queryset = im.Tutor.objects.select_related("especialidad", "ipress")
    serializer_class = TutorSerializer
    permission_classes = [IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]
    filterset_fields = ["especialidad", "ipress", "numero_documento", "activo"]
    search_fields = ["numero_documento", "nombres", "apellido_paterno"]
    ordering = ["id"]


# Catálogos del módulo (solo lectura): basename -> ViewSet
CATALOG_VIEWSETS = {
    "internship-statuses": _catalog_viewset(im.InternshipStatus),
    "rotation-statuses": _catalog_viewset(im.RotationStatus),
    "service-areas": _catalog_viewset(im.ServiceArea),
    "identity-document-types": _catalog_viewset(im.IdentityDocumentType),
}
