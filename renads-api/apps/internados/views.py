"""ViewSets del módulo Internados (bloque núcleo). Vistas delgadas: services/selectors."""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.http import HttpResponse

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404

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

from apps.internados.serializers import StudentBulkUploadSerializer, StudentSerializer, TutorConvenioSerializer, TutorSerializer
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


def _derivar_universidad_del_usuario(usuario) -> University:
    """Deriva la universidad del perfil institucional del usuario para la carga masiva.

    Usa ``entidades_del_usuario`` (fuente canónica, misma que ``estudiantes_visibles``).
    Si el usuario pertenece a exactamente una universidad, la devuelve.
    Admins y superusuarios no tienen perfil de universidad — deben enviar ``universidad_id``.
    """
    from rest_framework.exceptions import ValidationError as DRFValidationError
    from apps.common.selectors import entidades_del_usuario

    es_admin = usuario.is_superuser or usuario.groups.filter(name="Administrador RENADS").exists()
    if es_admin:
        raise DRFValidationError({
            "universidad_id": (
                "Los administradores deben enviar universidad_id en el formulario "
                "al realizar carga masiva."
            )
        })

    ct_uni = ContentType.objects.get_for_model(University).id
    refs = entidades_del_usuario(usuario)
    uni_ids = [oid for (tc, oid) in refs if tc == ct_uni]

    if len(uni_ids) == 1:
        try:
            return University.objects.get(pk=int(uni_ids[0]))
        except (University.DoesNotExist, ValueError):
            pass

    if len(uni_ids) > 1:
        raise DRFValidationError({
            "universidad_id": (
                "El usuario pertenece a más de una universidad. "
                "Envíe universidad_id en el formulario para indicar cuál usar."
            )
        })

    raise DRFValidationError({
        "universidad_id": (
            "No se encontró perfil de universidad para este usuario. "
            "Envíe universidad_id en el formulario."
        )
    })


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

        `universidad_id` es opcional en el cuerpo: si no se envía se deriva del perfil
        institucional del usuario. Si el usuario pertenece a más de una universidad debe
        especificarla explícitamente.
        """
        ser = StudentBulkUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        universidad = ser.validated_data.get("universidad_id")
        if universidad is None:
            universidad = _derivar_universidad_del_usuario(request.user)

        resumen = services.registrar_estudiantes_masivo(
            archivo=ser.validated_data["archivo"],
            usuario=request.user,
            universidad=universidad,
            periodo_internado=ser.validated_data.get("periodo_internado_id"),
        )
        return Response(resumen, status=200)

    @action(detail=False, methods=["get"], url_path="bulk-template")
    def bulk_template(self, request):
        """Descarga la plantilla Excel de carga masiva según nivel académico.

        Parámetro de query ``nivel_academico=PREGRADO`` (por defecto) genera la trama
        con la columna ``carrera_profesional``. Cualquier otro valor genera la trama
        con la columna ``especialidad`` (segunda especialidad, maestría, doctorado).
        """
        nivel = request.query_params.get("nivel_academico", "PREGRADO")
        es_pregrado = nivel.upper() == "PREGRADO"
        datos = services.generar_trama_excel(es_pregrado=es_pregrado)
        sufijo = "PREGRADO" if es_pregrado else "noPREGRADO"
        nombre_archivo = f"TramaCargaMasivaEstudiantes_{sufijo}.xlsx"
        respuesta = HttpResponse(
            datos,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
        return respuesta


class TutorViewSet(AuditedModelViewSet):
    """CRUD de tutores/docentes. Escritura por rol Universidad/Administrador.

    Acciones anidadas `convenios` y `convenio_detail` permiten gestionar los vínculos
    del tutor con Convenios Específicos e IPRESS (tabla `tutor_convenio`).
    """

    queryset = im.Tutor.objects.select_related(
        "especialidad", "profesion", "tipo_documento_identidad"
    ).prefetch_related("universidades")
    serializer_class = TutorSerializer
    permission_classes = [IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]
    filterset_fields = ["especialidad", "universidades", "numero_documento", "activo"]
    search_fields = ["numero_documento", "nombres", "apellido_paterno"]
    ordering = ["id"]

    @action(detail=False, methods=["get"], url_path="buscar")
    def buscar(self, request):
        """Busca un tutor por tipo y número de documento.

        Parámetros requeridos: ``tipo_documento_identidad`` (id) y ``numero_documento`` (str).
        Devuelve 200+datos si existe, 404 si no, 400 si faltan parámetros.
        """
        tipo_doc = request.query_params.get("tipo_documento_identidad")
        numero_doc = request.query_params.get("numero_documento")
        if not tipo_doc or not numero_doc:
            return Response(
                {"detail": "Se requieren tipo_documento_identidad y numero_documento."},
                status=400,
            )
        tutor = self.get_queryset().filter(
            tipo_documento_identidad_id=tipo_doc,
            numero_documento=numero_doc.strip(),
        ).first()
        if tutor is None:
            return Response({"detail": "No encontrado."}, status=404)
        ser = self.get_serializer(tutor)
        return Response(ser.data)

    @action(detail=True, methods=["get", "post"], url_path="convenios")
    def convenios(self, request, pk=None):
        """Lista o crea vínculos tutor ↔ Convenio Específico ↔ IPRESS.

        - GET: retorna todos los `TutorConvenio` del tutor.
        - POST: crea un nuevo vínculo; requiere rol `Universidad` o `Administrador RENADS`.
        """
        tutor = self.get_object()
        if request.method == "POST":
            exigir_roles(request, "Universidad", "Administrador RENADS")
            ser = TutorConvenioSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            tc = services.crear_tutor_convenio(
                tutor=tutor,
                convenio=ser.validated_data["convenio"],
                ipress=ser.validated_data["ipress"],
                usuario=request.user,
            )
            return Response(TutorConvenioSerializer(tc).data, status=201)
        qs = selectors.convenios_del_tutor(tutor)
        return Response(TutorConvenioSerializer(qs, many=True).data)

    @action(detail=True, methods=["get", "delete"], url_path=r"convenios/(?P<convenio_pk>[^/.]+)")
    def convenio_detail(self, request, pk=None, convenio_pk=None):
        """Obtiene o elimina un vínculo tutor ↔ Convenio Específico.

        - GET: retorna el vínculo individual.
        - DELETE: elimina el vínculo; requiere rol `Universidad` o `Administrador RENADS`.
        """
        tutor = self.get_object()
        tc = get_object_or_404(im.TutorConvenio, tutor=tutor, convenio_id=convenio_pk)
        if request.method == "DELETE":
            exigir_roles(request, "Universidad", "Administrador RENADS")
            services.eliminar_tutor_convenio(tutor_convenio=tc, usuario=request.user)
            return Response(status=204)
        return Response(TutorConvenioSerializer(tc).data)


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
    "internship-periods": _entity_viewset(
        im.InternshipPeriod, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "annex-documents": _entity_viewset(
        im.AnnexDocument,
        filterset_fields=["tipo_actor", "obligatorio", "activo"],
        search_fields=["codigo", "nombre"],
    ),
}
