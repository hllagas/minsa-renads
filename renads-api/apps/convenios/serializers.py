"""Serializers del módulo Convenios (bloque núcleo + entradas de flujo)."""

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

    class Meta:
        model = Convention
        fields = [
            "id", "tipo_convenio", "convenio_marco", "plantilla", "codigo", "titulo",
            "solicitante_tipo_contenido", "solicitante_id_objeto", "solicitante",
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
            "fecha_solicitud", "fecha_inicio", "fecha_fin", "max_campos_clinicos",
        ]


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
