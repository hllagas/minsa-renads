"""Serializers del módulo Internados (bloque núcleo + entradas de flujo)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.internados import services
from apps.internados.models import (
    Student,
    Internship,
    InternshipStatusHistory,
    Rotation,
    RotationAuthorization,
    RotationStatusHistory,
    Tutor,
    TutorHistory,
)


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = ["creado_por", "creado_en"]

    def validate(self, attrs):
        """RN-19: valida periodo académico vs. especialidad según el nivel académico.

        En updates parciales fusiona los valores del ``instance`` cuando no vienen
        en ``attrs``. Delega la regla en el helper único de ``services`` (fuente
        única de verdad, compartida con la carga masiva).
        """
        attrs = super().validate(attrs)

        def _valor(campo):
            if campo in attrs:
                return attrs[campo]
            if self.instance is not None:
                return getattr(self.instance, campo)
            return None

        carrera = _valor("carrera_profesional")
        if carrera is None:
            return attrs  # sin carrera no se puede derivar el nivel; otras validaciones lo cubren
        try:
            services.validar_regla_periodo_especialidad(
                carrera=carrera,
                periodo_academico=_valor("periodo_academico"),
                especialidad=_valor("especialidad"),
            )
        except (serializers.ValidationError, DjangoValidationError) as exc:
            raise serializers.ValidationError(getattr(exc, "detail", None) or getattr(exc, "message_dict", str(exc)))
        return attrs


class StudentBulkUploadSerializer(serializers.Serializer):
    """Entrada de la carga masiva de estudiantes (RN-16): archivo Excel `.xlsx`."""

    archivo = serializers.FileField(help_text="Archivo Excel (.xlsx) con los estudiantes a registrar")


class TutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutor
        fields = "__all__"


# ---------------------------------------------------------------------------
# Internado
# ---------------------------------------------------------------------------
class InternshipReadSerializer(serializers.ModelSerializer):
    estudiante = serializers.StringRelatedField(read_only=True)
    convenio = serializers.CharField(source="convenio.titulo", read_only=True)
    ipress = serializers.CharField(source="ipress.nombre", read_only=True)
    tutor = serializers.StringRelatedField(read_only=True)
    estado_actual = serializers.CharField(source="estado_actual.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado_actual.codigo", read_only=True)

    class Meta:
        model = Internship
        fields = [
            "id", "estudiante", "convenio", "campo_clinico", "ipress", "tutor",
            "ambito_geografico_sanitario", "estado_actual", "estado_codigo",
            "estado_declaraciones",
            "fecha_inicio", "fecha_fin", "observaciones",
            "creado_por", "creado_en", "actualizado_en",
        ]


class InternshipWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Internship
        fields = [
            "estudiante", "convenio", "campo_clinico", "ipress", "tutor",
            "ambito_geografico_sanitario", "fecha_inicio", "fecha_fin", "observaciones",
        ]


class InternshipUpdateSerializer(serializers.ModelSerializer):
    """Solo campos editables del internado (el tutor se cambia con `cambiar-tutor`)."""

    class Meta:
        model = Internship
        fields = ["ipress", "observaciones", "fecha_inicio", "fecha_fin"]
        extra_kwargs = {
            "ipress": {"required": False},
            "observaciones": {"required": False},
            "fecha_inicio": {"required": False},
            "fecha_fin": {"required": False},
        }


class InternshipStatusHistorySerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source="estado.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado.codigo", read_only=True)

    class Meta:
        model = InternshipStatusHistory
        fields = ["id", "estado", "estado_codigo", "cambiado_por", "cambiado_en", "observacion"]


class TutorHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorHistory
        fields = ["id", "tutor", "fecha_cambio", "motivo", "responsable", "creado_en"]


# ---------------------------------------------------------------------------
# Rotación
# ---------------------------------------------------------------------------
class RotationReadSerializer(serializers.ModelSerializer):
    estado_actual = serializers.CharField(source="estado_actual.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado_actual.codigo", read_only=True)

    class Meta:
        model = Rotation
        fields = [
            "id", "interno", "numero_rotacion", "ipress_origen", "ipress_destino",
            "servicio_area", "estado_actual", "estado_codigo",
            "fecha_inicio", "fecha_fin", "observaciones", "creado_por", "creado_en",
        ]


class RotationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rotation
        fields = [
            "ipress_origen", "ipress_destino", "servicio_area",
            "fecha_inicio", "fecha_fin", "observaciones",
        ]


class RotationStatusHistorySerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source="estado.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado.codigo", read_only=True)

    class Meta:
        model = RotationStatusHistory
        fields = ["id", "estado", "estado_codigo", "cambiado_por", "cambiado_en", "observacion"]


# ---------------------------------------------------------------------------
# Entradas de acciones
# ---------------------------------------------------------------------------
class CambiarEstadoInternadoSerializer(serializers.Serializer):
    estado_codigo = serializers.CharField()
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class CambiarEstadoRotacionSerializer(serializers.Serializer):
    estado_codigo = serializers.CharField()
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class RevisarDeclaracionesSerializer(serializers.Serializer):
    """Entrada de la revisión de declaraciones juradas (RN-23)."""

    resultado = serializers.ChoiceField(choices=["VALIDADAS", "OBSERVADAS"])
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class CambiarTutorSerializer(serializers.Serializer):
    tutor = serializers.PrimaryKeyRelatedField(queryset=Tutor.objects.all())
    fecha_cambio = serializers.DateField()
    motivo = serializers.CharField()


class RotationAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotationAuthorization
        fields = ["participante_convenio", "resultado", "fecha_autorizacion", "observaciones"]
