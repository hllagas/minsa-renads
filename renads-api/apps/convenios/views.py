"""ViewSets del módulo Convenios (bloque núcleo). Vistas delgadas: delegan en services/selectors."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import ProtectedError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsInstitutionalMember, IsModuleEnabled, exigir_ambito
from apps.common.services import adjuntar_documento, registrar_auditoria
from apps.common.storage import get_document_storage
from apps.convenios import models as m
from apps.convenios.mixins import AnnexAttachmentMixin, LogoStorageMixin
from apps.convenios import selectors, services
from apps.convenios.filters import (
    AuditLogFilter,
    ClinicalFieldAllocationFilter,
    ClinicalFieldRegistrationFilter,
    ConventionFilter,
)
from apps.convenios.models import ConventionTemplate
from apps.convenios.permissions import (
    ConventionScope,
    IsAdminRole,
    IsAdminRoleOrReadOnly,
    IsConapresOrReadOnly,
    IsRegionalOrganOrReadOnly,
    exigir_roles,
)
from apps.convenios.serializers import (
    AuditLogSerializer,
    SolicitanteContentTypeSerializer,
    CambiarEstadoSerializer,
    ClinicalFieldAllocationSerializer,
    ClinicalFieldRegistrationSerializer,
    ConapresOpinionSerializer,
    ConventionParticipantSerializer,
    ConventionReadSerializer,
    ConventionStatusHistorySerializer,
    ConventionTemplateSerializer,
    ConventionWriteSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentWriteSerializer,
    LegalOpinionSerializer,
    OrganRepresentativeSerializer,
    PublicationSerializer,
    SignatureSerializer,
    TechnicalEvaluationSerializer,
)


class ConventionViewSet(viewsets.ModelViewSet):
    """CRUD de convenios y acciones de flujo. Escritura vía services; lectura vía selectors."""

    permission_classes = [IsAuthenticated, IsInstitutionalMember, ConventionScope, IsModuleEnabled]
    module_content_type = ("convenios", "convention")
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


class ProtectedDeleteConflict(APIException):
    """El registro no se puede borrar porque otras filas lo referencian con FK protegida (409)."""

    status_code = 409
    default_detail = "No se puede eliminar: el registro está referenciado por otros datos."
    default_code = "protected_delete"


class AuditedModelViewSet(viewsets.ModelViewSet):
    """ModelViewSet que registra create/update/delete en `bitacora_auditoria` (RNF-AUD-01)."""

    def perform_create(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "CREAR", objeto)

    def perform_update(self, serializer):
        objeto = serializer.save()
        registrar_auditoria(self.request.user, "ACTUALIZAR", objeto)

    def perform_destroy(self, instance):
        # `instance.delete()` lanza ProtectedError si hay FK protegidas → devolver 409 legible
        # en vez de un 500. Django anula `instance.pk` tras borrar, por eso se restaura para auditar.
        pk = instance.pk
        try:
            instance.delete()
        except ProtectedError as exc:
            modelos = sorted({str(obj._meta.verbose_name) for obj in exc.protected_objects})
            raise ProtectedDeleteConflict(
                "No se puede eliminar: el registro está referenciado por "
                + ", ".join(modelos)
                + ". Elimina o reasigna esos registros primero."
            )
        instance.pk = pk
        registrar_auditoria(self.request.user, "ELIMINAR", instance)


class ConventionTemplateViewSet(AuditedModelViewSet):
    """CRUD de plantillas de convenio (escritura solo Administrador RENADS)."""

    queryset = ConventionTemplate.objects.all()
    serializer_class = ConventionTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]


class ClinicalFieldRegistrationViewSet(AuditedModelViewSet):
    """CRUD del registro (CONAPRES) del total de campos clínicos por sede + carrera.

    Escritura solo CONAPRES; lectura para autenticados. La escritura delega en los
    services (`crear_/actualizar_registro_campo_clinico`), que fijan
    `creado_por`/`actualizado_por` y registran la auditoría. Por eso se sobrescriben
    `perform_create`/`perform_update` (llaman al service) evitando la doble auditoría
    de `AuditedModelViewSet`.
    """

    serializer_class = ClinicalFieldRegistrationSerializer
    permission_classes = [IsAuthenticated, IsConapresOrReadOnly]
    filterset_class = ClinicalFieldRegistrationFilter
    ordering = ["id"]

    def get_queryset(self):
        return selectors.registros_campo_clinico()

    def perform_create(self, serializer):
        serializer.instance = services.crear_registro_campo_clinico(
            datos=serializer.validated_data, usuario=self.request.user
        )

    def perform_update(self, serializer):
        serializer.instance = services.actualizar_registro_campo_clinico(
            registro=serializer.instance,
            datos=serializer.validated_data,
            usuario=self.request.user,
        )


class ClinicalFieldAllocationViewSet(AuditedModelViewSet):
    """CRUD de la asignación (Órgano Regional) de campos clínicos por universidad.

    Escritura solo grupo `Gobierno Regional`; lectura para autenticados. La
    escritura delega en los services (`crear_/actualizar_/eliminar_asignacion_campo_clinico`),
    que recalculan el acumulador del registro padre y registran la auditoría; se
    sobrescriben `perform_create`/`perform_update`/`perform_destroy` para no duplicar
    la auditoría de `AuditedModelViewSet`. El `PROTECT` de `Internship` sobre la
    asignación se traduce a 409 vía `ProtectedDeleteConflict`.
    """

    serializer_class = ClinicalFieldAllocationSerializer
    permission_classes = [IsAuthenticated, IsRegionalOrganOrReadOnly]
    filterset_class = ClinicalFieldAllocationFilter
    ordering = ["id"]

    def get_queryset(self):
        return selectors.asignaciones_campo_clinico()

    def perform_create(self, serializer):
        serializer.instance = services.crear_asignacion_campo_clinico(
            datos=serializer.validated_data, usuario=self.request.user
        )

    def perform_update(self, serializer):
        serializer.instance = services.actualizar_asignacion_campo_clinico(
            asignacion=serializer.instance,
            datos=serializer.validated_data,
            usuario=self.request.user,
        )

    def perform_destroy(self, instance):
        try:
            services.eliminar_asignacion_campo_clinico(
                asignacion=instance, usuario=self.request.user
            )
        except ProtectedError as exc:
            modelos = sorted({str(obj._meta.verbose_name) for obj in exc.protected_objects})
            raise ProtectedDeleteConflict(
                "No se puede eliminar: el registro está referenciado por "
                + ", ".join(modelos)
                + ". Elimina o reasigna esos registros primero."
            )


# ---------------------------------------------------------------------------
# Bloque 2 — Catálogos (solo lectura) y entidades (CRUD)
# ---------------------------------------------------------------------------
def _detalle_nombre(rel):
    """Detalle legible de una FK con `nombre` (catálogos, entidades).

    Incluye `codigo` cuando el modelo relacionado lo tiene (todos los que derivan de
    `Catalog`: categoría, clasificación, ámbito, microrred), para que el listado pueda
    mostrar el código o el nombre según convenga.
    """
    return {"id": rel.id, "codigo": getattr(rel, "codigo", None), "nombre": rel.nombre}


def _detalle_ubigeo(rel):
    """Detalle legible de un UBIGEO (no tiene `nombre`)."""
    return {
        "id": rel.id,
        "codigo": getattr(rel, "codigo", None),
        "distrito": rel.distrito,
        "provincia": rel.provincia,
        "departamento": rel.departamento,
    }


def _auto_serializer(model, detalles=None):
    """Crea un ModelSerializer con todos los campos del modelo.

    Para las entidades con logo (`ImageField` `referencia_logo`), expone el campo
    como URL de solo lectura (`.url` = signed URL efímero con django-storages, o
    `None` si no hay logo). El logo NO se sube por el CRUD, sino por `upload-logo`.

    `detalles` (opcional): mapa `{nombre_fk: extractor}` que añade un campo de solo
    lectura `{nombre_fk}_detalle` con el detalle legible de esa FK (p. ej. `{id, nombre}`),
    sin alterar los campos de escritura (la FK sigue enviándose por id). Útil para que
    los listados muestren nombres sin resolver ids en el frontend.
    """
    meta = type("Meta", (), {"model": model, "fields": "__all__"})
    atributos = {"Meta": meta}

    campos = {f.name for f in model._meta.get_fields()}
    if "referencia_logo" in campos:
        def _get_referencia_logo(self, obj):
            """URL del logo institucional (o `None` si no hay logo cargado)."""
            return obj.referencia_logo.url if obj.referencia_logo else None

        atributos["referencia_logo"] = drf_serializers.SerializerMethodField()
        atributos["get_referencia_logo"] = _get_referencia_logo

    for nombre_fk, extractor in (detalles or {}).items():
        def _make_getter(field_name, extract):
            def getter(self, obj):
                rel = getattr(obj, field_name, None)
                return extract(rel) if rel is not None else None
            return getter

        atributos[f"{nombre_fk}_detalle"] = drf_serializers.SerializerMethodField()
        atributos[f"get_{nombre_fk}_detalle"] = _make_getter(nombre_fk, extractor)

    return type(f"{model.__name__}AutoSerializer", (drf_serializers.ModelSerializer,), atributos)


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


def _entity_viewset(
    model,
    *,
    filterset_fields=None,
    search_fields=None,
    permission_classes=None,
    logo=False,
    annex_actor=None,
    detalles=None,
):
    """ModelViewSet (CRUD) para una entidad. Escritura solo Administrador RENADS; con auditoría.

    Parámetros de adjunto real (Etapa 2 de `spec/almacenamiento.md`):
    - `logo=True` incluye `LogoStorageMixin` (acciones `upload-logo`/`logo-url`);
      requiere que el modelo tenga columna `referencia_logo`.
    - `annex_actor` (uno de `ANNEX_ACTOR`) incluye `AnnexAttachmentMixin`
      (acciones `annex-upload`/`annex-checklist`) fijando ese actor.
    """
    bases = []
    if logo:
        bases.append(LogoStorageMixin)
    if annex_actor:
        bases.append(AnnexAttachmentMixin)
    bases.append(AuditedModelViewSet)

    atributos = {
        "queryset": model._default_manager.all(),
        "serializer_class": _auto_serializer(model, detalles=detalles),
        "permission_classes": permission_classes or [IsAuthenticated, IsAdminRoleOrReadOnly],
        "filterset_fields": filterset_fields or [],
        "search_fields": search_fields or [],
        "ordering": ["id"],
    }
    if annex_actor:
        atributos["annex_actor"] = annex_actor
    return type(f"{model.__name__}ViewSet", tuple(bases), atributos)


class IpressViewSet(
    LogoStorageMixin,
    _entity_viewset(
        m.Ipress,
        filterset_fields=[
            "unidad_ejecutora", "ambito_geografico_sanitario", "es_sede_docente",
            "categoria", "tipo_clasificacion", "microred", "activo",
        ],
        search_fields=["nombre", "codigo_renipress"],
    ),
):
    """CRUD de IPRESS + autorización como sede docente por CONAPRES + logo."""

    # Lectura con detalle legible de las FKs (los listados muestran nombres, no ids). La escritura
    # sigue igual (cada FK se envía por id). `select_related` evita N+1 al serializar el detalle.
    queryset = m.Ipress._default_manager.select_related(
        "categoria",
        "tipo_clasificacion",
        "ambito_geografico_sanitario",
        "microred",
        "ubigeo",
    ).all()
    serializer_class = _auto_serializer(
        m.Ipress,
        detalles={
            "categoria": _detalle_nombre,
            "tipo_clasificacion": _detalle_nombre,
            "ambito_geografico_sanitario": _detalle_nombre,
            "microred": _detalle_nombre,
            "ubigeo": _detalle_ubigeo,
        },
    )

    @action(detail=True, methods=["post"], url_path="autorizar-sede-docente")
    def autorizar_sede_docente(self, request, pk=None):
        """CONAPRES autoriza/registra la IPRESS como sede docente. Body: `{autorizar: bool}` (default True)."""
        ipress = self.get_object()
        exigir_roles(request, "CONAPRES")
        autorizar = request.data.get("autorizar", True)
        if isinstance(autorizar, str):
            autorizar = autorizar.strip().lower() not in ("false", "0", "no", "")
        services.autorizar_sede_docente(ipress=ipress, usuario=request.user, autorizar=bool(autorizar))
        return Response(self.get_serializer(ipress).data)


# Catálogos (solo lectura): basename -> ViewSet
CATALOG_VIEWSETS = {
    "regions": _catalog_viewset(m.Region),
    "convention-types": _catalog_viewset(m.ConventionType),
    "convention-statuses": _catalog_viewset(m.ConventionStatus),
    "university-management-types": _catalog_viewset(m.UniversityManagementType),
    "specialties": _catalog_viewset(m.Specialty),
    "signing-authority-types": _catalog_viewset(m.SigningAuthorityType),
    "observation-reasons": _catalog_viewset(m.ObservationReason),
    "rejection-reasons": _catalog_viewset(m.RejectionReason),
    "closure-reasons": _catalog_viewset(m.ClosureReason),
}

# Entidades (CRUD): basename -> ViewSet
ENTITY_VIEWSETS = {
    # Catálogos maestros con CRUD (escritura solo Administrador RENADS; con auditoría).
    "organs": _entity_viewset(m.Organ, filterset_fields=["estado"], search_fields=["nombre"]),
    "health-geographic-scopes": _entity_viewset(
        m.HealthGeographicScope, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "executive-positions": _entity_viewset(
        m.ExecutivePosition,
        filterset_fields=["organo", "activo"],
        search_fields=["codigo", "nombre"],
        detalles={"organo": _detalle_nombre},
    ),
    "authorization-types": _entity_viewset(
        m.AuthorizationType, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "academic-levels": _entity_viewset(
        m.AcademicLevel, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "organ-types": _entity_viewset(
        m.OrganType,
        filterset_fields={"organo": ["exact"], "organo__nombre": ["exact", "icontains"], "activo": ["exact"]},
        search_fields=["codigo", "nombre"],
        detalles={"organo": _detalle_nombre},
    ),
    "categories": _entity_viewset(
        m.Category, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "classification-types": _entity_viewset(
        m.ClassificationType, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "networks": _entity_viewset(
        m.Red,
        filterset_fields=["ambito_geografico_sanitario", "activo"],
        search_fields=["codigo", "nombre"],
    ),
    "micro-networks": _entity_viewset(
        m.Microred, filterset_fields=["red", "activo"], search_fields=["codigo", "nombre"]
    ),
    "regional-governments": _entity_viewset(
        m.RegionalGovernment, filterset_fields=["region", "activo"], search_fields=["nombre"], logo=True
    ),
    "organ-directories": _entity_viewset(
        m.OrganDirectory,
        filterset_fields=["organo", "tipo_organo", "gobierno_regional", "activo"],
        search_fields=["nombre", "siglas", "numero_ruc"],
        logo=True,
        detalles={
            "organo": _detalle_nombre,
            "tipo_organo": _detalle_nombre,
            "gobierno_regional": _detalle_nombre,
        },
    ),
    "executing-units": _entity_viewset(
        m.ExecutingUnit,
        filterset_fields=["organo_regional", "tipo_organo", "estado"],
        search_fields=["nombre"],
        detalles={
            "organo_regional": _detalle_nombre,
            "tipo_organo": _detalle_nombre,
            "ubigeo": _detalle_ubigeo,
        },
    ),
    "ipress": IpressViewSet,
    "conapres": _entity_viewset(m.Conapres, filterset_fields=["activo"], search_fields=["nombre"]),
    "universities": _entity_viewset(
        m.University,
        filterset_fields=["tipo_gestion", "tipo_entidad", "tipo_autorizacion", "activo"],
        search_fields=["nombre", "siglas", "numero_ruc"],
        logo=True,
        detalles={
            "tipo_gestion": _detalle_nombre,
            "tipo_entidad": _detalle_nombre,
            "tipo_autorizacion": _detalle_nombre,
        },
    ),
    "faculties": _entity_viewset(
        m.Faculty, filterset_fields=["universidad", "activo"], search_fields=["nombre"]
    ),
    "professional-careers": _entity_viewset(
        m.ProfessionalCareer,
        filterset_fields=["nivel_academico", "activo"],
        search_fields=["nombre"],
    ),
    "university-careers": _entity_viewset(
        m.UniversityCareer,
        filterset_fields=["universidad", "carrera_profesional", "activo"],
        detalles={
            "universidad": _detalle_nombre,
            "carrera_profesional": _detalle_nombre,
        },
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


class OrganRepresentativeViewSet(AnnexAttachmentMixin, AuditedModelViewSet):
    """CRUD de representantes de órgano (FK directo al directorio) + adjunto real de anexos.

    Escritura solo Administrador RENADS. Al crear, delega en el service
    `registrar_organo_representante` (da de baja al anterior activo del mismo par
    `(organo_directorio, cargo_ejecutivo)` y lo copia al histórico). Adjunta PDFs
    de anexos del actor `REPRESENTANTE` (resolución del cargo, documento de
    identidad) vía `annex-upload`/`annex-checklist`.
    """

    queryset = m.OrganRepresentative.objects.select_related(
        "organo_directorio", "cargo_ejecutivo", "tipo_documento_identidad"
    )
    serializer_class = OrganRepresentativeSerializer
    permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]
    filterset_fields = ["organo_directorio", "cargo_ejecutivo", "activo"]
    search_fields = ["nombre", "numero_documento_identidad"]
    ordering = ["id"]
    annex_actor = "REPRESENTANTE"

    def perform_create(self, serializer):
        serializer.instance = services.registrar_organo_representante(
            datos=serializer.validated_data, usuario=self.request.user
        )


class OrganRepresentativeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Histórico de bajas de representantes de órgano (solo lectura)."""

    queryset = m.OrganRepresentativeHistory.objects.select_related(
        "representante", "organo_directorio", "cargo_ejecutivo"
    ).all()
    serializer_class = _auto_serializer(m.OrganRepresentativeHistory)
    permission_classes = [IsAuthenticated]
    filterset_fields = ["organo_directorio", "cargo_ejecutivo", "representante"]
    ordering = ["-fecha_baja", "-id"]


# ---------------------------------------------------------------------------
# Soporte transversal — Documento y bitácora de auditoría
# ---------------------------------------------------------------------------
class DocumentViewSet(AuditedModelViewSet):
    """Gestión documental polimórfica con versionado (RNF-DOC-01/02/03/04).

    Las nuevas versiones se crean adjuntando otro documento al mismo objeto (no
    hay update/partial_update); la lógica de versionado vive en el service.
    """

    queryset = m.Document.objects.select_related(
        "documento_anexo", "tipo_contenido", "version_anterior", "cargado_por"
    )
    permission_classes = [IsAuthenticated, IsInstitutionalMember]
    filterset_fields = ["tipo_contenido", "id_objeto", "documento_anexo", "estado"]
    ordering = ["-id"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    @property
    def storage(self):
        """Backend de almacenamiento seleccionado por settings (GCS o stub)."""
        return get_document_storage()

    def get_serializer_class(self):
        if self.action == "create":
            return DocumentWriteSerializer
        if self.action == "upload":
            return DocumentUploadSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        ser = DocumentWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tipo_contenido = ser.validated_data["tipo_contenido"]
        objeto = tipo_contenido.get_object_for_this_type(pk=ser.validated_data["id_objeto"])
        documento = adjuntar_documento(
            objeto,
            referencia_externa=ser.validated_data["referencia_externa"],
            usuario=request.user,
            documento_anexo=ser.validated_data["documento_anexo"],
        )
        return Response(DocumentSerializer(documento).data, status=201)

    @extend_schema(request=DocumentUploadSerializer, responses=DocumentSerializer)
    @action(
        detail=False,
        methods=["post"],
        url_path="upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload(self, request):
        """Sube el binario al backend y adjunta el documento versionado.

        Flujo: valida tipo/tamaño → sube vía `storage.subir(...)` (obtiene la key
        como `referencia_externa`) → `adjuntar_documento(...)` (versionado +
        auditoría, ya cubiertos por el service). Ruta: `POST /api/v1/documents/upload/`
        (multipart/form-data).
        """
        ser = DocumentUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        datos = ser.validated_data
        tipo_contenido = datos["tipo_contenido"]
        objeto = tipo_contenido.get_object_for_this_type(pk=datos["id_objeto"])
        archivo = datos["archivo"]
        referencia = self.storage.subir(archivo, ruta=datos["nombre_archivo"])
        documento = adjuntar_documento(
            objeto,
            referencia_externa=referencia,
            usuario=request.user,
            documento_anexo=datos["documento_anexo"],
        )
        return Response(DocumentSerializer(documento).data, status=201)

    def perform_destroy(self, instance):
        # Elimina el binario en el backend seleccionado (GCS o no-op en el stub).
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


# Entidades que pueden ser solicitantes de un convenio (relación polimórfica `solicitante`).
SOLICITANTE_MODELS = (
    m.University,
    m.Ipress,
    m.RegionalGovernment,
    m.ExecutingUnit,
    m.OrganDirectory,
    m.Conapres,
)


class SolicitanteContentTypeView(APIView):
    """Lista los `ContentType` elegibles como entidad solicitante de un convenio.

    El frontend usa esta lista para el selector «Tipo de entidad solicitante»: el `id`
    es el valor que espera `solicitante_tipo_contenido`, y `model` permite elegir el
    endpoint de la entidad concreta. Los ids de `ContentType` dependen de la base de
    datos, por eso se exponen vía API en lugar de fijarse en el cliente.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=SolicitanteContentTypeSerializer(many=True),
        summary="Tipos de entidad solicitante",
        description=(
            "Lista los ContentType elegibles como entidad solicitante de un convenio. "
            "El `id` es el valor que espera `solicitante_tipo_contenido` y `model` permite "
            "resolver el endpoint de la entidad concreta."
        ),
        tags=["convenios"],
    )
    def get(self, request):
        cts = ContentType.objects.get_for_models(*SOLICITANTE_MODELS)
        data = [
            {"id": ct.id, "app_label": ct.app_label, "model": ct.model}
            for ct in cts.values()
        ]
        data.sort(key=lambda item: item["id"])
        return Response(SolicitanteContentTypeSerializer(data, many=True).data)
