"""Serializers del módulo Convenios (bloque núcleo + entradas de flujo)."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.convenios.models import (
    AuditLog,
    ClinicalField,
    ConapresOpinion,
    Convention,
    ConventionParticipant,
    ConventionStatusHistory,
    ConventionTemplate,
    Document,
    DocumentType,
    LegalOpinion,
    Publication,
    Representative,
    Signature,
    TechnicalEvaluation,
)

# Modelos a los que puede apuntar un representante (relación polimórfica).
ENTIDADES_REPRESENTABLES = {"minsaorgan", "regionalorgan", "executingunit", "ipress", "conapres"}


# ---------------------------------------------------------------------------
# Convenio
# ---------------------------------------------------------------------------
class ConventionReadSerializer(serializers.ModelSerializer):
    tipo_convenio = serializers.CharField(source="tipo_convenio.nombre", read_only=True)
    estado_actual = serializers.CharField(source="estado_actual.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado_actual.codigo", read_only=True)
    solicitante = serializers.SerializerMethodField()
    # Universidad y órgano regional: id + nombre legible; el "tipo" se deriva de la entidad
    # (no se almacena en `convenio`), evitando redundancia en el esquema.
    organo_regional_nombre = serializers.CharField(source="organo_regional.nombre", read_only=True)
    tipo_organo_regional = serializers.CharField(
        source="organo_regional.tipo_organo_regional.nombre", read_only=True
    )
    universidad_nombre = serializers.CharField(source="universidad.nombre", read_only=True)
    tipo_entidad_universidad = serializers.CharField(
        source="universidad.tipo_entidad.nombre", read_only=True
    )

    class Meta:
        model = Convention
        fields = [
            "id", "tipo_convenio", "convenio_marco", "plantilla", "codigo", "titulo",
            "solicitante_tipo_contenido", "solicitante_id_objeto", "solicitante",
            "organo_regional", "organo_regional_nombre", "tipo_organo_regional",
            "universidad", "universidad_nombre", "tipo_entidad_universidad",
            "estado_actual", "estado_codigo", "fecha_solicitud", "fecha_inicio", "fecha_fin",
            "max_campos_clinicos", "creado_por", "creado_en", "actualizado_en",
        ]

    def get_solicitante(self, obj) -> str:
        return str(obj.solicitante) if obj.solicitante else ""


class ConventionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Convention
        fields = [
            "tipo_convenio", "convenio_marco", "plantilla", "codigo", "titulo",
            "solicitante_tipo_contenido", "solicitante_id_objeto",
            "organo_regional", "universidad",
            "fecha_solicitud", "fecha_inicio", "fecha_fin", "max_campos_clinicos",
        ]


class SolicitanteContentTypeSerializer(serializers.Serializer):
    """Tipo de entidad elegible como solicitante de un convenio (`ContentType`).

    `id` es el valor que espera `solicitante_tipo_contenido`; `model` permite al cliente
    resolver el endpoint de la entidad concreta. Los ids dependen de la base de datos.
    """

    id = serializers.IntegerField(help_text="ID del ContentType (valor de solicitante_tipo_contenido)")
    app_label = serializers.CharField(help_text="App de Django (p. ej. convenios)")
    model = serializers.CharField(help_text="Modelo de Django (p. ej. university, conapres)")


class ConventionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConventionTemplate
        fields = "__all__"


class ConventionParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConventionParticipant
        fields = [
            "id", "convenio", "tipo_contenido", "id_objeto",
            "tipo_autoridad_firmante", "es_firmante", "creado_en",
        ]
        read_only_fields = ["convenio", "creado_en"]


class ConventionStatusHistorySerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source="estado.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado.codigo", read_only=True)

    class Meta:
        model = ConventionStatusHistory
        fields = ["id", "estado", "estado_codigo", "cambiado_por", "cambiado_en", "observacion"]


# ---------------------------------------------------------------------------
# Entradas de las acciones de flujo (convenio se toma de la URL)
# ---------------------------------------------------------------------------
class CambiarEstadoSerializer(serializers.Serializer):
    estado_codigo = serializers.CharField()
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class TechnicalEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicalEvaluation
        fields = ["resultado", "observaciones", "subsanacion", "organo_minsa", "fecha_evaluacion"]


class ConapresOpinionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConapresOpinion
        fields = ["fecha_solicitud", "estado_atencion", "resultado_opinion", "fecha_respuesta"]


class ClinicalFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalField
        fields = [
            "ipress", "carrera_profesional", "especialidad", "cantidad_maxima",
            "vigencia_inicio", "vigencia_fin", "ambito_geografico_sanitario", "observaciones",
        ]


class LegalOpinionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalOpinion
        fields = [
            "fecha_envio", "resultado_opinion", "observaciones_legales",
            "subsanacion", "fecha_respuesta",
        ]


class SignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = [
            "firmante_tipo_contenido", "firmante_id_objeto", "tipo_autoridad_firmante",
            "orden_firma", "fecha_envio", "fecha_recepcion", "estado_firma", "observaciones",
        ]


class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = ["fecha_publicacion", "referencia_publicacion"]


class RepresentativeSerializer(serializers.ModelSerializer):
    """Representante polimórfico; valida que apunte a una entidad permitida."""

    class Meta:
        model = Representative
        fields = "__all__"

    def validate_tipo_contenido(self, value):
        if value.model not in ENTIDADES_REPRESENTABLES:
            raise serializers.ValidationError(
                "La entidad representada debe ser órgano MINSA, órgano regional, "
                "unidad ejecutora, IPRESS o CONAPRES."
            )
        return value

    def validate(self, attrs):
        tipo = attrs.get("tipo_contenido")
        id_objeto = attrs.get("id_objeto")
        if tipo is not None and id_objeto is not None:
            modelo = tipo.model_class()
            if modelo is None or not modelo._default_manager.filter(pk=id_objeto).exists():
                raise serializers.ValidationError(
                    {"id_objeto": "La entidad referenciada no existe."}
                )
        return attrs


# ---------------------------------------------------------------------------
# Documento (gestión documental polimórfica con versionado)
# ---------------------------------------------------------------------------
class DocumentSerializer(serializers.ModelSerializer):
    """Lectura de documentos: incluye etiquetas legibles del tipo y la entidad destino."""

    tipo_documento_nombre = serializers.CharField(source="tipo_documento.nombre", read_only=True)
    tipo_contenido_label = serializers.CharField(source="tipo_contenido.model", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "tipo_documento", "tipo_documento_nombre",
            "tipo_contenido", "tipo_contenido_label", "id_objeto",
            "referencia_externa", "nombre_archivo", "version", "estado",
            "version_anterior", "cargado_por", "cargado_en",
        ]
        read_only_fields = [
            "version", "estado", "version_anterior", "cargado_por", "cargado_en",
        ]


class DocumentWriteSerializer(serializers.ModelSerializer):
    """Escritura de documentos: el versionado y el estado los fija el service."""

    class Meta:
        model = Document
        fields = [
            "tipo_contenido", "id_objeto", "tipo_documento",
            "nombre_archivo", "referencia_externa",
        ]

    def validate(self, attrs):
        tipo_contenido = attrs.get("tipo_contenido")
        id_objeto = attrs.get("id_objeto")
        try:
            tipo_contenido.get_object_for_this_type(pk=id_objeto)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"id_objeto": "El objeto destino indicado no existe."}
            )
        return attrs


# Extensiones aceptadas por content-type, como refuerzo a la validación MIME.
EXTENSIONES_POR_CONTENT_TYPE = {
    "application/pdf": {".pdf"},
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
}


class DocumentUploadSerializer(serializers.Serializer):
    """Subida real de un documento (multipart): valida tipo y tamaño del binario.

    Recibe el binario en `archivo` junto con los metadatos necesarios para
    adjuntarlo a un objeto (relación genérica). El versionado y la auditoría los
    resuelve el service `adjuntar_documento`; este serializer solo valida la
    entrada. Mensajes de error en español.
    """

    archivo = serializers.FileField(help_text="Binario a subir (PDF o imagen)")
    tipo_documento = serializers.PrimaryKeyRelatedField(
        queryset=DocumentType.objects.all(), help_text="Tipo de documento"
    )
    tipo_contenido = serializers.PrimaryKeyRelatedField(
        queryset=ContentType.objects.all(), help_text="Tabla destino"
    )
    id_objeto = serializers.IntegerField(min_value=1, help_text="Registro destino")
    nombre_archivo = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Nombre del archivo (si falta, se deriva del archivo subido)",
    )

    def validate_archivo(self, archivo):
        content_type = getattr(archivo, "content_type", "") or ""
        if content_type not in settings.GCS_ALLOWED_CONTENT_TYPES:
            permitidos = ", ".join(settings.GCS_ALLOWED_CONTENT_TYPES)
            raise serializers.ValidationError(
                f"Tipo de archivo no permitido. Se aceptan únicamente: {permitidos}."
            )
        extension = ("." + archivo.name.rsplit(".", 1)[-1].lower()) if "." in archivo.name else ""
        extensiones_validas = EXTENSIONES_POR_CONTENT_TYPE.get(content_type, set())
        if extension not in extensiones_validas:
            raise serializers.ValidationError(
                "La extensión del archivo no corresponde con su tipo de contenido."
            )
        if archivo.size > settings.GCS_MAX_UPLOAD_BYTES:
            maximo_mb = settings.GCS_MAX_UPLOAD_BYTES / (1024 * 1024)
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({maximo_mb:.0f} MiB)."
            )
        return archivo

    def validate(self, attrs):
        tipo_contenido = attrs.get("tipo_contenido")
        id_objeto = attrs.get("id_objeto")
        try:
            tipo_contenido.get_object_for_this_type(pk=id_objeto)
        except ObjectDoesNotExist:
            raise serializers.ValidationError(
                {"id_objeto": "El objeto destino indicado no existe."}
            )
        if not attrs.get("nombre_archivo"):
            attrs["nombre_archivo"] = attrs["archivo"].name
        return attrs


# ---------------------------------------------------------------------------
# Subida de logos institucionales (imágenes) — Etapa 2
# ---------------------------------------------------------------------------
# Content-types aceptados para logos: solo imágenes (se excluye PDF a propósito).
LOGO_CONTENT_TYPES = ["image/png", "image/jpeg", "image/webp"]


class LogoUploadSerializer(serializers.Serializer):
    """Subida del logo de una entidad (multipart): valida tipo y tamaño del binario.

    Solo acepta imágenes (`image/png`, `image/jpeg`, `image/webp`); rechaza PDF.
    El logo se guarda como una única key en `referencia_logo` de la entidad (sin
    versionado, sin `Document`). Mensajes de error en español.
    """

    archivo = serializers.FileField(help_text="Imagen del logo (PNG, JPEG o WEBP)")

    def validate_archivo(self, archivo):
        content_type = getattr(archivo, "content_type", "") or ""
        if content_type not in LOGO_CONTENT_TYPES:
            permitidos = ", ".join(LOGO_CONTENT_TYPES)
            raise serializers.ValidationError(
                f"Tipo de imagen no permitido. Se aceptan únicamente: {permitidos}."
            )
        extension = ("." + archivo.name.rsplit(".", 1)[-1].lower()) if "." in archivo.name else ""
        extensiones_validas = EXTENSIONES_POR_CONTENT_TYPE.get(content_type, set())
        if extension not in extensiones_validas:
            raise serializers.ValidationError(
                "La extensión del archivo no corresponde con su tipo de contenido."
            )
        if archivo.size > settings.GCS_MAX_UPLOAD_BYTES:
            maximo_mb = settings.GCS_MAX_UPLOAD_BYTES / (1024 * 1024)
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({maximo_mb:.0f} MiB)."
            )
        return archivo


# ---------------------------------------------------------------------------
# Subida de anexos (PDFs de declaraciones juradas por actor) — Etapa 2
# ---------------------------------------------------------------------------
class ActiveAnnexDocumentField(serializers.PrimaryKeyRelatedField):
    """PK del anexo activo (`documentos_anexos`), con queryset perezoso.

    Resuelve el modelo `internados.AnnexDocument` en `get_queryset` (import
    perezoso) para evitar el ciclo de import convenios <-> internados.
    """

    def get_queryset(self):
        from apps.internados.models import AnnexDocument

        return AnnexDocument.objects.filter(activo=True)


class AnnexUploadSerializer(serializers.Serializer):
    """Subida del PDF de un anexo (declaración jurada) por actor (multipart).

    Solo acepta `application/pdf`. El anexo (`documento_anexo`) referencia el
    catálogo maestro `internados.AnnexDocument`; el enforcement de que su
    `tipo_actor` coincide con la entidad destino lo hace el mixin (necesita el
    `annex_actor` del ViewSet). El versionado por `(objeto, documento_anexo)` lo
    resuelve el service `adjuntar_documento`. Mensajes de error en español.
    """

    documento_anexo = ActiveAnnexDocumentField(
        pk_field=serializers.IntegerField(),
        help_text="Anexo del catálogo maestro (documentos_anexos) que se adjunta",
    )
    archivo = serializers.FileField(help_text="Archivo PDF del anexo")
    nombre_archivo = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Nombre del archivo (si falta, se deriva del archivo subido)",
    )

    def validate_archivo(self, archivo):
        content_type = getattr(archivo, "content_type", "") or ""
        if content_type != "application/pdf":
            raise serializers.ValidationError(
                "Tipo de archivo no permitido. El anexo debe adjuntarse en formato PDF."
            )
        extension = ("." + archivo.name.rsplit(".", 1)[-1].lower()) if "." in archivo.name else ""
        if extension != ".pdf":
            raise serializers.ValidationError(
                "La extensión del archivo no corresponde con su tipo de contenido (se espera .pdf)."
            )
        if archivo.size > settings.GCS_MAX_UPLOAD_BYTES:
            maximo_mb = settings.GCS_MAX_UPLOAD_BYTES / (1024 * 1024)
            raise serializers.ValidationError(
                f"El archivo supera el tamaño máximo permitido ({maximo_mb:.0f} MiB)."
            )
        return archivo

    def validate(self, attrs):
        if not attrs.get("nombre_archivo"):
            attrs["nombre_archivo"] = attrs["archivo"].name
        return attrs


# ---------------------------------------------------------------------------
# Bitácora de auditoría (solo lectura)
# ---------------------------------------------------------------------------
class AuditLogSerializer(serializers.ModelSerializer):
    """Lectura de la bitácora de auditoría (RNF-AUD-01/02). Todos los campos read-only."""

    usuario_nombre = serializers.SerializerMethodField()
    tipo_contenido_label = serializers.CharField(source="tipo_contenido.model", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "usuario", "usuario_nombre", "accion",
            "tipo_contenido", "tipo_contenido_label", "id_objeto",
            "nombre_campo", "valor_anterior", "valor_nuevo",
            "direccion_ip", "creado_en",
        ]
        read_only_fields = fields

    def get_usuario_nombre(self, obj) -> str:
        return obj.usuario.get_username() if obj.usuario else ""
