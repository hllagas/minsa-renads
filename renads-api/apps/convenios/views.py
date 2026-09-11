"""ViewSets del módulo Convenios (bloque núcleo). Vistas delgadas: delegan en services/selectors."""

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import ProtectedError
from drf_spectacular.utils import extend_schema, inline_serializer
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
    AdendaWriteSerializer,
    AuditLogSerializer,
    SolicitanteContentTypeSerializer,
    CambiarEstadoSerializer,
    ClinicalFieldAllocationBulkUploadSerializer,
    ClinicalFieldAllocationSerializer,
    ClinicalFieldRegistrationBulkUploadSerializer,
    ClinicalFieldRegistrationSerializer,
    ConapresOpinionSerializer,
    ConventionBulkUploadSerializer,
    ConventionParticipantSerializer,
    ConventionPartySerializer,
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
    FacultyCareersSyncSerializer,
    SignatureSerializer,
    TechnicalEvaluationSerializer,
    UniversityCareerSerializer,
)


class ConventionViewSet(AnnexAttachmentMixin, viewsets.ModelViewSet):
    """CRUD de convenios y acciones de flujo. Escritura vía services; lectura vía selectors.

    `AnnexAttachmentMixin` (annex_actor="CONVENIO") habilita
    `conventions/{id}/annex-upload` y `conventions/{id}/annex-checklist` para adjuntar
    las resoluciones PDF del convenio/adenda (RESOL_MARCO/RESOL_ESPECIFICO/RESOL_ADENDA)
    versionadas por `(convenio, documento_anexo)`.
    """

    annex_actor = "CONVENIO"
    permission_classes = [IsAuthenticated, IsInstitutionalMember, ConventionScope, IsModuleEnabled]
    module_content_type = ("convenios", "convention")
    filterset_class = ConventionFilter
    search_fields = ["titulo", "nomenclatura"]
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

    @extend_schema(
        request=ConventionPartySerializer(many=True),
        responses=ConventionPartySerializer(many=True),
    )
    @action(detail=True, methods=["get", "post"], url_path="parties")
    def parties(self, request, pk=None):
        """Partes firmantes del convenio (rol + órgano + representante + cargo).

        GET lista las partes; POST recibe la lista completa y la sincroniza
        (crear/actualizar/eliminar) vía `services.sincronizar_partes`.
        """
        convenio = self.get_object()
        if request.method == "POST":
            ser = ConventionPartySerializer(data=request.data, many=True)
            ser.is_valid(raise_exception=True)
            partes = services.sincronizar_partes(
                convenio=convenio, datos=ser.validated_data, usuario=request.user
            )
            return Response(ConventionPartySerializer(partes, many=True).data)
        qs = convenio.partes_firmantes.select_related(
            "organo_directorio", "organo_representante", "cargo_ejecutivo"
        ).order_by("orden", "id")
        return Response(ConventionPartySerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="adenda")
    def adenda(self, request, pk=None):
        """Crea una adenda de ampliación del convenio (nuevo periodo de vigencia).

        Hereda del origen tipo, marco, universidad, órgano, unidad ejecutora,
        facultad y solicitante. El alcance institucional se valida contra la entidad
        solicitante del convenio origen (mismo criterio que crear un convenio).
        """
        convenio_origen = self.get_object()
        exigir_ambito(
            request.user,
            convenio_origen.solicitante_tipo_contenido_id,
            convenio_origen.solicitante_id_objeto,
        )
        ser = AdendaWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        adenda = services.crear_adenda(
            convenio_origen=convenio_origen,
            datos=ser.validated_data,
            usuario=request.user,
        )
        return Response(ConventionReadSerializer(adenda).data, status=201)

    def _adjuntar_pdf_generado(self, convenio, pdf_bytes, codigo_anexo, request):
        """Sube un PDF generado al storage y lo versiona como `Document` (helper interno).

        Resuelve el `documento_anexo` por `codigo`, sube el binario al backend activo
        y llama `adjuntar_documento` (versionado por `(objeto, documento_anexo)` +
        auditoría). Devuelve el `Document` creado.
        """
        import io

        from apps.internados.models import AnnexDocument

        try:
            anexo = AnnexDocument.objects.get(codigo=codigo_anexo)
        except AnnexDocument.DoesNotExist as exc:
            raise APIException(
                f"No existe el documento anexo '{codigo_anexo}'; ejecute las "
                "migraciones de datos del proyecto."
            ) from exc

        buffer = io.BytesIO(pdf_bytes)
        buffer.name = f"{codigo_anexo.lower()}_{convenio.pk}.pdf"
        buffer.content_type = "application/pdf"
        referencia = self.storage.subir(buffer, ruta=buffer.name)
        return adjuntar_documento(
            convenio,
            referencia_externa=referencia,
            usuario=request.user,
            documento_anexo=anexo,
        )

    @extend_schema(request=None, responses=DocumentSerializer)
    @action(detail=True, methods=["post"], url_path="generar-proyecto")
    def generar_proyecto(self, request, pk=None):
        """Genera el proyecto de convenio (PDF), lo sube y lo versiona como `Document`.

        Renderiza la plantilla del convenio (docxtpl), la convierte a PDF (LibreOffice)
        y la adjunta con el anexo `PROYECTO_ADENDA` si es adenda o `PROYECTO_CONVENIO`
        en otro caso. Escritura: pasa el gate `IsModuleEnabled` del ViewSet.
        """
        from apps.convenios import pdf

        convenio = self.get_object()
        pdf_bytes = pdf.generar_proyecto(convenio)
        codigo = "PROYECTO_ADENDA" if convenio.es_adenda else "PROYECTO_CONVENIO"
        documento = self._adjuntar_pdf_generado(convenio, pdf_bytes, codigo, request)
        return Response(DocumentSerializer(documento).data, status=201)

    @extend_schema(request=None, responses=DocumentSerializer)
    @action(detail=True, methods=["post"], url_path="generar-expediente")
    def generar_expediente(self, request, pk=None):
        """Genera el expediente consolidado (proyecto + adjuntos), lo sube y lo versiona.

        Concatena (pypdf) el proyecto con las resoluciones de los representantes
        firmantes y de los campos clínicos CONAPRES, y lo adjunta con el anexo
        `EXPEDIENTE`. Escritura: pasa el gate `IsModuleEnabled` del ViewSet.
        """
        from apps.convenios import pdf

        convenio = self.get_object()
        pdf_bytes = pdf.generar_expediente(convenio)
        documento = self._adjuntar_pdf_generado(convenio, pdf_bytes, "EXPEDIENTE", request)
        return Response(DocumentSerializer(documento).data, status=201)

    @action(
        detail=False, methods=["post"], url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=ConventionBulkUploadSerializer,
    )
    def bulk_upload(self, request):
        """Carga masiva de convenios (Marco y Específico) ya suscritos/publicados.

        Solo disponible para el rol ``Administrador RENADS``. El archivo Excel
        debe seguir la estructura de la trama `TramaCargaMasivaConvenios.xlsx`.
        Devuelve un resumen: ``{creados, omitidos, errores}``.
        """
        exigir_roles(request, "Administrador RENADS")
        ser = ConventionBulkUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resumen = services.registrar_convenios_masivo(
            archivo=ser.validated_data["archivo"], usuario=request.user
        )
        return Response(resumen, status=200)


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


class ClinicalFieldRegistrationViewSet(AnnexAttachmentMixin, AuditedModelViewSet):
    """CRUD del registro (CONAPRES) del total de campos clínicos por sede + carrera.

    Escritura solo CONAPRES; lectura para autenticados. La escritura delega en los
    services (`crear_/actualizar_registro_campo_clinico`), que fijan
    `creado_por`/`actualizado_por` y registran la auditoría. Por eso se sobrescriben
    `perform_create`/`perform_update` (llaman al service) evitando la doble auditoría
    de `AuditedModelViewSet`.

    `AnnexAttachmentMixin` (annex_actor="CAMPO_CLINICO") habilita
    `clinical-field-registrations/{id}/annex-upload` y `.../annex-checklist` para
    adjuntar la resolución CONAPRES (RESOL_CONAPRES) versionada por registro (D2).
    """

    annex_actor = "CAMPO_CLINICO"
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

    @action(
        detail=False, methods=["post"], url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=ClinicalFieldRegistrationBulkUploadSerializer,
    )
    def bulk_upload(self, request):
        """Carga masiva de determinación de campos clínicos.

        Disponible para los roles ``CONAPRES`` y ``Administrador RENADS``.
        El archivo Excel debe seguir la estructura de ``TramaDeterminacionCampos.xlsx``.
        Devuelve un resumen: ``{creados, omitidos, errores}``.
        """
        exigir_roles(request, "CONAPRES", "Administrador RENADS")
        ser = ClinicalFieldRegistrationBulkUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resumen = services.registrar_determinacion_masiva(
            archivo=ser.validated_data["archivo"], usuario=request.user
        )
        return Response(resumen, status=200)


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

    @action(
        detail=False, methods=["post"], url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=ClinicalFieldAllocationBulkUploadSerializer,
    )
    def bulk_upload(self, request):
        """Carga masiva de asignación de campos clínicos (solo Administrador RENADS).

        El archivo Excel debe seguir la estructura de ``TramaAsignacionCampos.xlsx``.
        Devuelve un resumen: ``{creados, omitidos, errores}``.
        """
        exigir_roles(request, "Administrador RENADS")
        ser = ClinicalFieldAllocationBulkUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        resumen = services.registrar_asignacion_masiva(
            archivo=ser.validated_data["archivo"], usuario=request.user
        )
        return Response(resumen, status=200)


# ---------------------------------------------------------------------------
# Bloque 2 — Catálogos (solo lectura) y entidades (CRUD)
# ---------------------------------------------------------------------------
def _detalle_nombre(rel):
    """Detalle legible de una FK con `nombre` (catálogos, entidades).

    Incluye `codigo` cuando el modelo relacionado lo tiene (todos los que derivan de
    `Catalog`: categoría, clasificación, ámbito, microrred), para que el listado pueda
    mostrar el código o el nombre según convenga.
    """
    # `pk` soporta PK numérica y textual (ipress `codigo_renipress`, executing-units `codigo`).
    return {"id": rel.pk, "codigo": getattr(rel, "codigo", None), "nombre": rel.nombre}


def _detalle_organo_directorio(rel):
    """Detalle legible de un órgano del directorio (`nombre` + su `organo` canónico)."""
    return {
        "id": rel.pk,
        "nombre": rel.nombre,
        "organo": getattr(rel.organo, "nombre", None),
    }


def _detalle_ubigeo(rel):
    """Detalle legible de un UBIGEO (no tiene `nombre`)."""
    return {
        "id": rel.pk,
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
    ordering=None,
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
        "ordering": ordering if ordering is not None else ["id"],
    }
    if annex_actor:
        atributos["annex_actor"] = annex_actor
    return type(f"{model.__name__}ViewSet", tuple(bases), atributos)


class _IpressSerializer(
    _auto_serializer(
        m.Ipress,
        detalles={
            "categoria": _detalle_nombre,
            "tipo_clasificacion": _detalle_nombre,
            "ambito_geografico_sanitario": _detalle_nombre,
            "microred": _detalle_nombre,
            "ubigeo": _detalle_ubigeo,
        },
    )
):
    """Serializer de IPRESS con validación de coherencia geográfica microred ↔ ámbito.

    Mantiene `fields="__all__"`, los `*_detalle` y el logo como URL de solo lectura del
    auto-serializer base. El auto-serializer (`ModelSerializer`) no ejecuta `Model.clean()`,
    por lo que aquí se engancha la RN de coherencia (ajuste B de la spec) resolviendo el
    estado final del objeto (create y PATCH parcial) contra `Ipress.clean()`.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Estado final del objeto: para PATCH parcial, se parte de la instancia y se
        # aplican los campos enviados; para create, solo los campos del payload.
        microred = attrs.get("microred", getattr(self.instance, "microred", None))
        ambito = attrs.get(
            "ambito_geografico_sanitario",
            getattr(self.instance, "ambito_geografico_sanitario", None),
        )
        instancia = m.Ipress(microred=microred, ambito_geografico_sanitario=ambito)
        try:
            instancia.clean()
        except DjangoValidationError as exc:
            raise drf_serializers.ValidationError(exc.message_dict)
        return attrs


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
    serializer_class = _IpressSerializer
    # La PK de Ipress es `codigo_renipress` (ya no existe `id`); el orden por defecto de
    # `_entity_viewset` es `["id"]`, que ya no aplica.
    ordering = ["codigo_renipress"]

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


class FacultyViewSet(
    _entity_viewset(
        m.Faculty,
        filterset_fields=["universidad", "ubigeo", "activo"],
        search_fields=["nombre", "direccion"],
        logo=True,
        detalles={"ubigeo": _detalle_ubigeo},
    ),
):
    """CRUD de facultades (con logo y ubigeo) + asignación en lote de carreras por facultad.

    La acción `careers` sincroniza (idempotente) las carreras de la facultad en
    `universidad_carrera` derivando la universidad de la facultad; delega en el
    service `sincronizar_carreras_facultad`.
    """

    queryset = m.Faculty._default_manager.select_related("universidad", "ubigeo").all()
    serializer_class = _auto_serializer(m.Faculty, detalles={"ubigeo": _detalle_ubigeo})

    @extend_schema(
        request=FacultyCareersSyncSerializer,
        responses=inline_serializer(
            name="FacultyCareersSyncResponse",
            fields={"carreras": UniversityCareerSerializer(many=True)},
        ),
    )
    @action(detail=True, methods=["post"], url_path="careers")
    def careers(self, request, pk=None):
        """Asigna en lote las carreras de la facultad. Body: `{carreras: [ids]}`.

        Escritura solo `Administrador RENADS`. Deriva la universidad de la facultad,
        da de alta/reactiva las carreras enviadas y de baja (por facultad) las que ya
        no estén. Devuelve las filas `universidad_carrera` activas resultantes.
        """
        facultad = self.get_object()
        exigir_roles(request, "Administrador RENADS")
        serializer = FacultyCareersSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        carreras = serializer.validated_data["carreras"]
        resultado = services.sincronizar_carreras_facultad(
            facultad=facultad, carreras_ids=carreras, usuario=request.user
        )
        return Response({"carreras": UniversityCareerSerializer(resultado, many=True).data})


class UniversityCareerViewSet(
    _entity_viewset(
        m.UniversityCareer,
        filterset_fields=["universidad", "carrera_profesional", "facultad", "activo"],
    ),
):
    """CRUD de carreras por universidad (puente universidad ↔ carrera ↔ facultad).

    Usa `UniversityCareerSerializer` (facultad requerida en escritura, RN-FC-02/03).
    """

    queryset = m.UniversityCareer._default_manager.select_related(
        "universidad", "carrera_profesional", "facultad"
    ).all()
    serializer_class = UniversityCareerSerializer


class _OrganDirectorySerializer(
    _auto_serializer(
        m.OrganDirectory,
        detalles={"organo": _detalle_nombre},
    )
):
    """Serializer de órganos del directorio con RN de unicidad `(organo, nombre)`.

    RN-GORE-3: el nombre no se repite dentro del mismo `organo`. El auto-serializer no
    aplica esta regla, así que se valida aquí y se devuelve un 400 legible en vez del
    IntegrityError 500 de la ``UniqueConstraint`` de la BD.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Estado final del objeto (soporta PATCH parcial partiendo de la instancia).
        organo = attrs.get("organo", getattr(self.instance, "organo", None))
        nombre = attrs.get("nombre", getattr(self.instance, "nombre", None))
        if organo is not None and nombre is not None:
            qs = m.OrganDirectory._default_manager.filter(organo=organo, nombre=nombre)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise drf_serializers.ValidationError(
                    {
                        "nombre": (
                            "Ya existe un órgano del directorio con este nombre para el "
                            "mismo órgano."
                        )
                    }
                )
        return attrs


class OrganDirectoryViewSet(
    _entity_viewset(
        m.OrganDirectory,
        filterset_fields=["organo", "activo"],
        search_fields=["nombre", "siglas"],
        detalles={"organo": _detalle_nombre},
    ),
):
    """CRUD del directorio unificado de órganos (RN: único por organo+nombre)."""

    queryset = m.OrganDirectory._default_manager.select_related(
        "organo"
    ).all()
    serializer_class = _OrganDirectorySerializer


class _ExecutivePositionSerializer(
    _auto_serializer(
        m.ExecutivePosition,
        detalles={
            "organo": _detalle_nombre,
            "organo_directivo": _detalle_organo_directorio,
        },
    )
):
    """Serializer de cargos ejecutivos con RN de coherencia `organo == organo_directivo.organo`.

    RN-CE-02: cuando `organo_directivo` está seteado, el `organo` del cargo debe coincidir
    con el `organo` de ese órgano directivo. El auto-serializer (`ModelSerializer`) no ejecuta
    `Model.clean()`, así que la coherencia se valida aquí y se devuelve un 400 legible.
    Si `organo_directivo` es nulo (cargo global), la coherencia no aplica; el FK `organo`
    obligatorio ya lo garantiza el propio `ModelSerializer` (campo requerido por `null=False`).
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Estado final del objeto (soporta PATCH parcial partiendo de la instancia).
        organo = attrs.get("organo", getattr(self.instance, "organo", None))
        organo_directivo = attrs.get(
            "organo_directivo", getattr(self.instance, "organo_directivo", None)
        )
        if organo_directivo is not None and organo is not None:
            if organo.id != organo_directivo.organo_id:
                raise drf_serializers.ValidationError(
                    {
                        "organo": (
                            "El órgano del cargo debe coincidir con el órgano del "
                            "órgano directivo seleccionado."
                        )
                    }
                )
        return attrs


class ExecutivePositionViewSet(
    _entity_viewset(
        m.ExecutivePosition,
        # `organo_directivo__isnull=true` lista los cargos globales (sin órgano directivo),
        # reutilizables por cualquier entidad (representantes multi-entidad).
        filterset_fields={
            "organo": ["exact"],
            "organo_directivo": ["exact", "isnull"],
            "activo": ["exact"],
        },
        search_fields=["nombre_masculino", "nombre_femenino"],
        detalles={
            "organo": _detalle_nombre,
            "organo_directivo": _detalle_organo_directorio,
        },
    ),
):
    """CRUD de cargos ejecutivos (RN de coherencia organo ↔ organo_directivo.organo)."""

    queryset = m.ExecutivePosition._default_manager.select_related(
        "organo", "organo_directivo"
    ).all()
    serializer_class = _ExecutivePositionSerializer


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
        m.HealthGeographicScope,
        filterset_fields=["activo"],
        search_fields=["codigo", "nombre"],
        detalles={"gobierno_regional": _detalle_nombre},
    ),
    "executive-positions": ExecutivePositionViewSet,
    "authorization-types": _entity_viewset(
        m.AuthorizationType, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
    ),
    "academic-levels": _entity_viewset(
        m.AcademicLevel, filterset_fields=["activo"], search_fields=["codigo", "nombre"]
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
        m.RegionalGovernment,
        filterset_fields=["region", "ubigeo", "activo"],
        search_fields=["nombre"],
        logo=True,
        detalles={"ubigeo": _detalle_ubigeo},
    ),
    "organ-directories": OrganDirectoryViewSet,
    "executing-units": _entity_viewset(
        m.ExecutingUnit,
        filterset_fields=["ambito_geografico_sanitario", "activo"],
        search_fields=["nombre", "codigo"],
        detalles={"ambito_geografico_sanitario": _detalle_nombre},
        ordering=["codigo"],
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
    "faculties": FacultyViewSet,
    "professional-careers": _entity_viewset(
        m.ProfessionalCareer,
        filterset_fields=["nivel_academico", "activo"],
        search_fields=["nombre"],
    ),
    "university-careers": UniversityCareerViewSet,
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
    """CRUD de representantes de entidad (relación polimórfica) + adjunto real de anexos.

    Escritura solo Administrador RENADS. Al crear, delega en el service
    `registrar_organo_representante` (da de baja al anterior activo del mismo par
    `(tipo_contenido, id_objeto, cargo_ejecutivo)` y lo copia al histórico). Adjunta
    PDFs de anexos del actor `REPRESENTANTE` (resolución del cargo, documento de
    identidad) vía `annex-upload`/`annex-checklist`.
    """

    # `entidad` es GenericForeignKey (no admite select_related); se precarga el ContentType.
    queryset = m.OrganRepresentative.objects.select_related(
        "tipo_contenido", "cargo_ejecutivo", "tipo_documento_identidad"
    )
    serializer_class = OrganRepresentativeSerializer
    permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]
    filterset_fields = ["tipo_contenido", "id_objeto", "cargo_ejecutivo", "activo"]
    search_fields = ["nombre", "numero_documento_identidad"]
    ordering = ["id"]
    annex_actor = "REPRESENTANTE"

    def perform_create(self, serializer):
        serializer.instance = services.registrar_organo_representante(
            datos=serializer.validated_data, usuario=self.request.user
        )


class OrganRepresentativeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Histórico de bajas de representantes de entidad (solo lectura)."""

    queryset = m.OrganRepresentativeHistory.objects.select_related(
        "representante", "tipo_contenido", "cargo_ejecutivo"
    ).all()
    serializer_class = _auto_serializer(m.OrganRepresentativeHistory)
    permission_classes = [IsAuthenticated]
    filterset_fields = ["tipo_contenido", "id_objeto", "cargo_ejecutivo", "representante"]
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


# Entidades cuyos representantes/autoridades se registran (relación polimórfica `entidad`).
# MINSA/GORE/DIRIS son el mismo modelo `OrganDirectory` (se discriminan por `organo` en
# el front), por eso NO incluye `RegionalGovernment` (a diferencia de SOLICITANTE_MODELS).
REPRESENTANTE_MODELS = (
    m.OrganDirectory,
    m.University,
    m.ExecutingUnit,
    m.Conapres,
    m.Ipress,
)


class RepresentanteContentTypeView(APIView):
    """Lista los `ContentType` elegibles como entidad de un representante/autoridad.

    El frontend usa esta lista para resolver `tipo_contenido` a partir del `model`
    (los ids de `ContentType` dependen de la BD, por eso se exponen vía API). Los 3
    «tipos» de OrganDirectory (MINSA/GORE/DIRIS) comparten el mismo ContentType y se
    distinguen en la UI por el filtro `categoria`.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=SolicitanteContentTypeSerializer(many=True),
        summary="Tipos de entidad de representante",
        description=(
            "Lista los ContentType elegibles como entidad de un representante. El `id` es "
            "el valor que espera `tipo_contenido` y `model` permite resolver el endpoint de "
            "la entidad concreta."
        ),
        tags=["convenios"],
    )
    def get(self, request):
        cts = ContentType.objects.get_for_models(*REPRESENTANTE_MODELS)
        data = [
            {"id": ct.id, "app_label": ct.app_label, "model": ct.model}
            for ct in cts.values()
        ]
        data.sort(key=lambda item: item["id"])
        return Response(SolicitanteContentTypeSerializer(data, many=True).data)
