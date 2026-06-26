"""Serializers del módulo Convenios (bloque núcleo + entradas de flujo)."""

from rest_framework import serializers

from apps.convenios.models import (
    ClinicalField,
    ConapresOpinion,
    Convention,
    ConventionParticipant,
    ConventionStatusHistory,
    ConventionTemplate,
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
