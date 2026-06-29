"""ViewSets del módulo Convenios (bloque núcleo). Vistas delgadas: delegan en services/selectors."""

from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsInstitutionalMember, exigir_ambito
from apps.common.services import adjuntar_documento, registrar_auditoria
from apps.common.storage import storage_por_defecto
from apps.convenios import models as m
from apps.convenios import selectors, services
from apps.convenios.filters import AuditLogFilter, ConventionFilter
from apps.convenios.models import ConventionTemplate
from apps.convenios.permissions import (
    ConventionScope,
    IsAdminRole,
    IsAdminRoleOrReadOnly,
    exigir_roles,
)
from apps.convenios.serializers import (
    AuditLogSerializer,
    CambiarEstadoSerializer,
    ClinicalFieldSerializer,
    ConapresOpinionSerializer,
    ConventionParticipantSerializer,
    ConventionReadSerializer,
    ConventionStatusHistorySerializer,
    ConventionTemplateSerializer,
    ConventionWriteSerializer,
    DocumentSerializer,
    DocumentWriteSerializer,
    LegalOpinionSerializer,
    PublicationSerializer,
    RepresentativeSerializer,
    SignatureSerializer,
    TechnicalEvaluationSerializer,
)


class ConventionViewSet(viewsets.ModelViewSet):
    """CRUD de convenios y acciones de flujo. Escritura vía services; lectura vía selectors."""

    permission_classes = [IsAuthenticated, IsInstitutionalMember, ConventionScope]
    filterset_class = ConventionFilter
    search_fields = ["titulo", "codigo"]
    ordering_fields = ["fecha_solicitud", "fecha_inicio", "fecha_fin", "id"]
    ordering = ["-id"]

    def get_queryset(self):
        return selectors.convenios_visibles(self.request.user)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ConventionReadSerializer
        return ConventionWriteSerializer

    def _read(self, convenio) -> Response:
        return Response(ConventionReadSerializer(convenio).data)

    def create(self, request, *args, **kwargs):
        ser = ConventionWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        exigir_ambito(
            request.user,
            ser.validated_data["solicitante_tipo_contenido"].id,
            ser.validated_data["solicitante_id_objeto"],
        )
        convenio = services.crear_convenio(datos=ser.validated_data, usuario=request.user)
        return Response(ConventionReadSerializer(convenio).data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        convenio = self.get_object()
        ser = ConventionWriteSerializer(convenio, data=request.data, partial=partial)
        ser.is_valid(raise_exception=True)
        convenio = services.actualizar_convenio(
            convenio=convenio, datos=ser.validated_data, usuario=request.user
        )
        return self._read(convenio)

    # --- Acciones de flujo ---
    @action(detail=True, methods=["post"], url_path="cambiar-estado")
    def cambiar_estado(self, request, pk=None):
        convenio = self.get_object()
        exigir_roles(request, "Administrador RENADS")
        ser = CambiarEstadoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        convenio = services.cambiar_estado(
            convenio=convenio,
            nuevo_estado_codigo=ser.validated_data["estado_codigo"],
            usuario=request.user,
            observacion=ser.validated_data.get("observacion", ""),
        )
        return self._read(convenio)

    @action(detail=True, methods=["post"], url_path="evaluacion-tecnica")
    def evaluacion_tecnica(self, request, pk=None):
        convenio = self.get_object()
        exigir_roles(request, "DIGEP")
        ser = TechnicalEvaluationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.registrar_evaluacion_tecnica(
            convenio=convenio, datos=ser.validated_data, usuario=request.user
        )
        return self._read(convenio)

    @action(detail=True, methods=["post"], url_path="opinion-conapres")
    def opinion_conapres(self, request, pk=None):
        convenio = self.get_object()
        exigir_roles(request, "CONAPRES")
        ser = ConapresOpinionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.registrar_opinion_conapres(
            convenio=convenio, datos=ser.validated_data, usuario=request.user
        )
        return self._read(convenio)

    @action(detail=True, methods=["get", "post"], url_path="campos-clinicos")
    def campos_clinicos(self, request, pk=None):
        convenio = self.get_object()
        if request.method == "POST":
            exigir_roles(request, "CONAPRES")
            ser = ClinicalFieldSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            services.definir_campo_clinico(
                convenio=convenio, datos=ser.validated_data, usuario=request.user
            )
        qs = selectors.campos_clinicos_de(convenio)
        return Response(ClinicalFieldSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="opinion-juridica")
    def opinion_juridica(self, request, pk=None):
        convenio = self.get_object()
        exigir_roles(request, "OGAJ")
        ser = LegalOpinionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.registrar_opinion_juridica(
            convenio=convenio, datos=ser.validated_data, usuario=request.user
        )
        return self._read(convenio)

    @action(detail=True, methods=["post"], url_path="firma")
    def firma(self, request, pk=None):
        convenio = self.get_object()
        exigir_roles(request, "Secretaría General")
        ser = SignatureSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.registrar_firma(convenio=convenio, datos=ser.validated_data, usuario=request.user)
        return self._read(convenio)

    @action(detail=True, methods=["post"], url_path="publicacion")
    def publicacion(self, request, pk=None):
        convenio = self.get_object()
        exigir_roles(request, "Secretaría General")
        ser = PublicationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.publicar_convenio(convenio=convenio, datos=ser.validated_data, usuario=request.user)
        return self._read(convenio)

    @action(detail=True, methods=["get", "post"], url_path="participantes")
    def participantes(self, request, pk=None):
        convenio = self.get_object()
        if request.method == "POST":
            exigir_roles(request, "Administrador RENADS")
            ser = ConventionParticipantSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            services.agregar_participante(
                convenio=convenio, datos=ser.validated_data, usuario=request.user
            )
        qs = selectors.participantes_de(convenio)
        return Response(ConventionParticipantSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        convenio = self.get_object()
        qs = selectors.historial_convenio(convenio)
        return Response(ConventionStatusHistorySerializer(qs, many=True).data)


class AuditedModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet que registra create/update/delete en `bitacora_auditoria` (RNF-AUD-01)."""

    def perform_create(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "CREAR", objeto)

    def perform_update(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "ACTUALIZAR", objeto)

    def perform_destroy(self, instance):
        registrar_auditoria(self.request.user, "ELIMINAR", instance)
        instance.delete()


class ConventionTemplateViewSet(AuditedModelViewSet):
    """CRUD de plantillas de convenio (escritura solo Administrador RENADS)."""

    queryset = ConventionTemplate.objects.all()
    serializer_class = ConventionTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]


# ---------------------------------------------------------------------------
# Bloque 2 — Catálogos (solo lectura) y entidades (CRUD)
# ---------------------------------------------------------------------------
def _auto_serializer(model):
    """Crea un ModelSerializer con todos los campos del modelo."""
    meta = type("Meta", (), {"model": model, "fields": "__all__"})
    return type(f"{model.__name__}AutoSerializer", (drf_serializers.ModelSerializer,), {"Meta": meta})


def _catalog_viewset(model):
    """ReadOnlyModelViewSet para un catálogo (list/retrieve)."""
    return type(
        f"{model.__name__}ViewSet",
        (viewsets.ReadOnlyModelViewSet,),
        {
            "queryset": model._default_manager.all(),
            "serializer_class": _auto_serializer(model),
            "permission_classes": [IsAuthenticated],
            "filterset_fields": ["activo"],
            "search_fields": ["codigo", "nombre"],
            "ordering_fields": ["id", "codigo", "nombre"],
            "ordering": ["id"],
        },
    )


def _entity_viewset(model, *, filterset_fields=None, search_fields=None, permission_classes=None):
    """ModelViewSet (CRUD) para una entidad. Escritura solo Administrador RENADS; con auditoría."""
    return type(
        f"{model.__name__}ViewSet",
        (AuditedModelViewSet,),
        {
            "queryset": model._default_manager.all(),
            "serializer_class": _auto_serializer(model),
            "permission_classes": permission_classes or [IsAuthenticated, IsAdminRoleOrReadOnly],
            "filterset_fields": filterset_fields or [],
            "search_fields": search_fields or [],
            "ordering": ["id"],
        },
    )


# Catálogos (solo lectura): basename -> ViewSet
CATALOG_VIEWSETS = {
    "regions": _catalog_viewset(m.Region),
    "health-geographic-scopes": _catalog_viewset(m.HealthGeographicScope),
    "convention-types": _catalog_viewset(m.ConventionType),
    "convention-statuses": _catalog_viewset(m.ConventionStatus),
    "document-types": _catalog_viewset(m.DocumentType),
    "university-management-types": _catalog_viewset(m.UniversityManagementType),
    "university-entity-types": _catalog_viewset(m.UniversityEntityType),
    "authorization-types": _catalog_viewset(m.AuthorizationType),
    "academic-levels": _catalog_viewset(m.AcademicLevel),
    "specialties": _catalog_viewset(m.Specialty),
    "signing-authority-types": _catalog_viewset(m.SigningAuthorityType),
    "regional-organ-types": _catalog_viewset(m.RegionalOrganType),
    "executing-unit-types": _catalog_viewset(m.ExecutingUnitType),
    "minsa-organ-types": _catalog_viewset(m.MinsaOrganType),
    "executive-positions": _catalog_viewset(m.ExecutivePosition),
    "observation-reasons": _catalog_viewset(m.ObservationReason),
    "rejection-reasons": _catalog_viewset(m.RejectionReason),
    "closure-reasons": _catalog_viewset(m.ClosureReason),
}

# Entidades (CRUD): basename -> ViewSet
ENTITY_VIEWSETS = {
    "regional-governments": _entity_viewset(
        m.RegionalGovernment, filterset_fields=["region", "activo"], search_fields=["nombre"]
    ),
    "regional-organs": _entity_viewset(
        m.RegionalOrgan,
        filterset_fields=["gobierno_regional", "tipo_organo_regional", "activo"],
        search_fields=["nombre", "siglas"],
    ),
    "executing-units": _entity_viewset(
        m.ExecutingUnit,
        filterset_fields=["organo_regional", "tipo_unidad_ejecutora", "activo"],
        search_fields=["nombre", "codigo"],
    ),
    "ipress": _entity_viewset(
        m.Ipress,
        filterset_fields=["unidad_ejecutora", "ambito_geografico_sanitario", "activo"],
        search_fields=["nombre", "codigo_renipress"],
    ),
    "minsa-organs": _entity_viewset(
        m.MinsaOrgan, filterset_fields=["tipo_organo_minsa", "activo"], search_fields=["nombre", "siglas"]
    ),
    "conapres": _entity_viewset(m.Conapres, filterset_fields=["activo"], search_fields=["nombre"]),
    "universities": _entity_viewset(
        m.University,
        filterset_fields=["tipo_gestion", "tipo_entidad", "tipo_autorizacion", "activo"],
        search_fields=["nombre", "siglas"],
    ),
    "university-authorities": _entity_viewset(
        m.UniversityAuthority, filterset_fields=["universidad", "activo"], search_fields=["nombre", "cargo"]
    ),
    "faculties": _entity_viewset(
        m.Faculty, filterset_fields=["universidad", "activo"], search_fields=["nombre"]
    ),
    "professional-careers": _entity_viewset(
        m.ProfessionalCareer,
        filterset_fields=["facultad", "nivel_academico", "especialidad", "activo"],
        search_fields=["nombre"],
    ),
    "university-campuses": _entity_viewset(
        m.UniversityCampus, filterset_fields=["universidad", "region", "activo"], search_fields=["nombre"]
    ),
    # Asignación de perfiles institucionales: solo Administrador RENADS (evita escalación de privilegios).
    "user-entity-profiles": _entity_viewset(
        m.UserEntityProfile,
        filterset_fields=["usuario", "grupo", "activo"],
        permission_classes=[IsAuthenticated, IsAdminRole],
    ),
}


class UbigeoViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de ubigeos (INEI), solo lectura."""

    queryset = m.Ubigeo.objects.all()
    serializer_class = _auto_serializer(m.Ubigeo)
    permission_classes = [IsAuthenticated]
    filterset_fields = ["departamento", "provincia", "distrito", "activo"]
    search_fields = ["codigo", "distrito", "provincia", "departamento"]
    ordering = ["codigo"]


class RepresentativeViewSet(AuditedModelViewSet):
    """CRUD de representantes (relación polimórfica validada). Escritura solo Administrador RENADS."""

    queryset = m.Representative.objects.select_related("tipo_contenido", "cargo_ejecutivo")
    serializer_class = RepresentativeSerializer
    permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]
    filterset_fields = ["tipo_contenido", "id_objeto", "cargo_ejecutivo", "activo"]
    ordering = ["id"]


# ---------------------------------------------------------------------------
# Soporte transversal — Documento y bitácora de auditoría
# ---------------------------------------------------------------------------
class DocumentViewSet(AuditedModelViewSet):
    """Gestión documental polimórfica con versionado (RNF-DOC-01/02/03/04).

    Las nuevas versiones se crean adjuntando otro documento al mismo objeto (no
    hay update/partial_update); la lógica de versionado vive en el service.
    """

    queryset = m.Document.objects.select_related(
        "tipo_documento", "tipo_contenido", "version_anterior", "cargado_por"
    )
    permission_classes = [IsAuthenticated, IsInstitutionalMember]
    filterset_fields = ["tipo_contenido", "id_objeto", "tipo_documento", "estado"]
    ordering = ["-id"]
    http_method_names = ["get", "post", "delete", "head", "options"]
    storage = storage_por_defecto

    def get_serializer_class(self):
        if self.action == "create":
            return DocumentWriteSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        ser = DocumentWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tipo_contenido = ser.validated_data["tipo_contenido"]
        objeto = tipo_contenido.get_object_for_this_type(pk=ser.validated_data["id_objeto"])
        documento = adjuntar_documento(
            objeto,
            tipo_documento=ser.validated_data["tipo_documento"],
            nombre_archivo=ser.validated_data["nombre_archivo"],
            referencia_externa=ser.validated_data["referencia_externa"],
            usuario=request.user,
        )
        return Response(DocumentSerializer(documento).data, status=201)

    def perform_destroy(self, instance):
        # Punto de integración del repositorio externo (stub no-op por ahora).
        self.storage.eliminar(instance.referencia_externa)
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"], url_path="url-descarga")
    def url_descarga(self, request, pk=None):
        documento = self.get_object()
        return Response({"url": self.storage.url_firmada(documento.referencia_externa)})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de la bitácora de auditoría (RNF-AUD-01/02). Restringida a Administrador/Auditor."""

    queryset = m.AuditLog.objects.select_related("usuario", "tipo_contenido").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filterset_class = AuditLogFilter
    search_fields = ["accion"]
    ordering_fields = ["creado_en", "id"]
    ordering = ["-creado_en"]
