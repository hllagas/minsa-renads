"""ViewSets del módulo Internados (bloque núcleo). Vistas delgadas: services/selectors."""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.contenttypes.models import ContentType

from apps.common.permissions import IsInstitutionalMember, IsModuleEnabled, exigir_ambito
from apps.common.services import registrar_auditoria
from apps.convenios.mixins import AnnexAttachmentMixin
from apps.convenios.models import University
from apps.convenios.serializers import AnnexUploadSerializer, DocumentSerializer
from apps.convenios.permissions import exigir_roles
from apps.convenios.views import AuditedModelViewSet, _catalog_viewset, _entity_viewset
from apps.internados import models as im
from apps.internados import selectors, services
from apps.internados.filters import InternshipFilter, RotationFilter, StudentFilter
from apps.internados.models import Rotation
from apps.internados.permissions import InternshipScope, IsUniversityOrReadOnly
from drf_spectacular.utils import extend_schema

from apps.internados.serializers import StudentBulkUploadSerializer, StudentSerializer, TutorSerializer
from apps.internados.serializers import (
    CambiarEstadoInternadoSerializer,
    CambiarEstadoRotacionSerializer,
    CambiarTutorSerializer,
    InternshipReadSerializer,
    InternshipStatusHistorySerializer,
    InternshipUpdateSerializer,
    InternshipWriteSerializer,
    RevisarDeclaracionesSerializer,
    RotationAuthorizationSerializer,
    RotationReadSerializer,
    RotationStatusHistorySerializer,
    RotationWriteSerializer,
)


class InternshipViewSet(AnnexAttachmentMixin, viewsets.ModelViewSet):
    """CRUD de internados y acciones de flujo. Escritura vía services; lectura vía selectors.

    Adjunto real de anexos (declaraciones juradas) del interno (actor `INTERNO`) vía
    `annex-upload`/`annex-checklist` (mixin transversal `AnnexAttachmentMixin`, T-F2.2):
    los PDFs se guardan como `Document` versionado por `(interno, documento_anexo)`.
    """

    permission_classes = [IsAuthenticated, IsInstitutionalMember, InternshipScope, IsUniversityOrReadOnly, IsModuleEnabled]
    module_content_type = ("internados", "internship")
    annex_actor = "INTERNO"
    filterset_class = InternshipFilter
    search_fields = ["estudiante__numero_documento", "estudiante__nombres", "estudiante__apellido_paterno"]
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
        estudiante = ser.validated_data["estudiante"]
        ct_uni = ContentType.objects.get_for_model(University).id
        exigir_ambito(request.user, ct_uni, estudiante.universidad_id)
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

    @extend_schema(request=RevisarDeclaracionesSerializer, responses=InternshipReadSerializer)
    @action(detail=True, methods=["post"], url_path="revisar-declaraciones")
    def revisar_declaraciones(self, request, pk=None):
        """Revisión humana de las declaraciones juradas del interno (RN-23).

        Rol `Universidad`/`Administrador RENADS`. `resultado` ∈ {VALIDADAS, OBSERVADAS}.
        """
        internado = self.get_object()
        exigir_roles(request, "Universidad", "Administrador RENADS")
        ser = RevisarDeclaracionesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        internado = services.revisar_declaraciones(
            internado=internado,
            resultado=ser.validated_data["resultado"],
            usuario=request.user,
            observacion=ser.validated_data.get("observacion", ""),
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

    @extend_schema(request=AnnexUploadSerializer, responses=DocumentSerializer)
    @action(
        detail=True, methods=["post"], url_path="annex-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def annex_upload(self, request, pk=None):
        """Adjunta el PDF de un anexo del interno y recalcula el estado de sus DJ (RN-23).

        Reutiliza la lógica del `AnnexAttachmentMixin` (adjunto versionado por
        `(interno, documento_anexo)`) y, tras adjuntar, recalcula
        `estado_declaraciones` del internado.
        """
        respuesta = AnnexAttachmentMixin.annex_upload(self, request, pk=pk)
        if respuesta.status_code == 201:
            services.recalcular_estado_declaraciones(self.get_object(), usuario=request.user)
        return respuesta


class RotationViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura de rotaciones y acciones de autorización/inicio/estado."""

    permission_classes = [IsAuthenticated, IsInstitutionalMember, InternshipScope]
    filterset_class = RotationFilter
    ordering_fields = ["numero_rotacion", "fecha_inicio", "id"]
    ordering = ["-id"]
    serializer_class = RotationReadSerializer

    def get_queryset(self):
        internados = selectors.internados_visibles(self.request.user)
        return Rotation.objects.filter(interno__in=internados).select_related(
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
# Bloque 2 — Catálogos (solo lectura) y personas (Student / Tutor)
# ---------------------------------------------------------------------------
class StudentViewSet(AuditedModelViewSet):
    """CRUD de estudiantes. Escritura por rol Universidad/Administrador; alcance por universidad.

    El adjunto real de anexos (declaraciones juradas) del interno se realiza sobre
    el internado (`InternshipViewSet`, acciones `annex-upload`/`annex-checklist`),
    no sobre el estudiante.
    """

    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]
    filterset_class = StudentFilter
    search_fields = ["numero_documento", "nombres", "apellido_paterno"]
    ordering = ["id"]

    def get_queryset(self):
        return selectors.estudiantes_visibles(self.request.user)

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

    @action(
        detail=False, methods=["post"], url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=StudentBulkUploadSerializer,
    )
    def bulk_upload(self, request):
        """Carga masiva de estudiantes desde un Excel (.xlsx) — RN-16.

        Escritura por rol Universidad/Administrador (misma política que el CRUD).
        El alcance institucional se valida por fila. Devuelve el resumen de la carga.
        """
        ser = StudentBulkUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resumen = services.registrar_estudiantes_masivo(
            archivo=ser.validated_data["archivo"], usuario=request.user
        )
        return Response(resumen, status=200)


class TutorViewSet(AuditedModelViewSet):
    """CRUD de tutores/docentes. Escritura por rol Universidad/Administrador."""

    queryset = im.Tutor.objects.select_related("especialidad", "ipress").prefetch_related("universidades")
    serializer_class = TutorSerializer
    permission_classes = [IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]
    filterset_fields = ["especialidad", "ipress", "universidades", "numero_documento", "activo"]
    search_fields = ["numero_documento", "nombres", "apellido_paterno"]
    ordering = ["id"]


# Catálogos del módulo (solo lectura): basename -> ViewSet
CATALOG_VIEWSETS = {
    "internship-statuses": _catalog_viewset(im.InternshipStatus),
    "rotation-statuses": _catalog_viewset(im.RotationStatus),
    "service-areas": _catalog_viewset(im.ServiceArea),
    "identity-document-types": _catalog_viewset(im.IdentityDocumentType),
    "relationship-types": _catalog_viewset(im.RelationshipType),
}

# Catálogos maestros con CRUD (escritura solo Administrador RENADS): basename -> ViewSet
ENTITY_VIEWSETS = {
    "academic-periods": _entity_viewset(
        im.AcademicPeriod, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "annex-documents": _entity_viewset(
        im.AnnexDocument,
        filterset_fields=["tipo_actor", "obligatorio", "activo"],
        search_fields=["codigo", "nombre"],
    ),
}
