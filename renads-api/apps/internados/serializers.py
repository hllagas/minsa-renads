"""Serializers del módulo Internados (bloque núcleo + entradas de flujo)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.convenios.models import Convention, Ipress, University
from apps.internados.models import InternshipPeriod
from apps.internados import services
from apps.internados.models import (
    Student,
    Internship,
    InternshipStatusHistory,
    Rotation,
    RotationAuthorization,
    RotationStatusHistory,
    Tutor,
    TutorConvenio,
    TutorHistory,
)


class StudentSerializer(serializers.ModelSerializer):
    # Detalles legibles para el listado (el estudiante no persiste `nivel_academico`; deriva de
    # la carrera — RN-19). Solo lectura; la escritura sigue por id.
    carrera_profesional_detalle = serializers.SerializerMethodField(read_only=True)
    especialidad_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = ["creado_por", "creado_en"]

    def get_carrera_profesional_detalle(self, obj):
        c = obj.carrera_profesional
        if c is None:
            return None
        return {"id": c.id, "nombre": c.nombre, "nivel_academico": c.nivel_academico_id}

    def get_especialidad_detalle(self, obj):
        e = obj.especialidad
        if e is None:
            return None
        return {"id": e.id, "nombre": e.nombre}

    def validate_nota_promedio_ponderado(self, value):
        if value is None:
            return value
        if value < 0 or value > 20:
            raise serializers.ValidationError("La nota debe estar entre 0 y 20.")
        return value

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
                periodo_internado=_valor("periodo_internado"),
                especialidad=_valor("especialidad"),
            )
        except (serializers.ValidationError, DjangoValidationError) as exc:
            raise serializers.ValidationError(getattr(exc, "detail", None) or getattr(exc, "message_dict", str(exc)))
        return attrs


class StudentBulkUploadSerializer(serializers.Serializer):
    """Entrada de la carga masiva de estudiantes (RN-16): archivo Excel `.xlsx`.

    `universidad_id` es opcional: si no se envía, la vista lo deriva del perfil
    institucional del usuario (válido cuando el usuario pertenece a una sola universidad).
    `periodo_internado_id` aplica solo a filas PREGRADO; se ignora en las demás.
    """

    archivo = serializers.FileField(help_text="Archivo Excel (.xlsx) con los estudiantes a registrar")
    universidad_id = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        required=False,
        allow_null=True,
        help_text="Universidad que aplica a todos los estudiantes del archivo. Si no se envía, se deriva del perfil del usuario.",
    )
    periodo_internado_id = serializers.PrimaryKeyRelatedField(
        queryset=InternshipPeriod.objects.all(),
        required=False,
        allow_null=True,
        help_text="Periodo de internado (solo para estudiantes PREGRADO); opcional",
    )


class TutorSerializer(serializers.ModelSerializer):
    """CRUD de tutores. `universidades` (RN-24): de 1 a 2 universidades por tutor."""

    universidades = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(), many=True,
        help_text="Universidades del tutor (de 1 a 2 — RN-24)",
    )
    # Detalles legibles para el listado (lectura; la escritura sigue por id).
    profesion_detalle = serializers.SerializerMethodField(read_only=True)
    especialidad_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Tutor
        fields = "__all__"

    def get_profesion_detalle(self, obj):
        p = obj.profesion
        return {"id": p.id, "nombre": p.nombre} if p else None

    def get_especialidad_detalle(self, obj):
        e = obj.especialidad
        return {"id": e.id, "nombre": e.nombre} if e else None

    def validate_universidades(self, value):
        # RN-24: fuente única de la regla (1..2 universidades, sin repetidos).
        services.validar_universidades_tutor(value)
        return value

    def create(self, validated_data):
        universidades = validated_data.pop("universidades")
        tutor = super().create(validated_data)
        tutor.universidades.set(universidades)
        return tutor

    def update(self, instance, validated_data):
        universidades = validated_data.pop("universidades", None)
        tutor = super().update(instance, validated_data)
        if universidades is not None:
            tutor.universidades.set(universidades)
        return tutor


class TutorConvenioSerializer(serializers.ModelSerializer):
    """Serializer del vínculo tutor ↔ Convenio Específico ↔ IPRESS."""

    tutor = serializers.PrimaryKeyRelatedField(read_only=True)
    convenio = serializers.PrimaryKeyRelatedField(queryset=Convention.objects.all())
    ipress = serializers.PrimaryKeyRelatedField(queryset=Ipress.objects.all())
    convenio_detalle = serializers.SerializerMethodField(read_only=True)
    ipress_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TutorConvenio
        fields = ["id", "tutor", "convenio", "ipress", "convenio_detalle", "ipress_detalle"]

    def get_convenio_detalle(self, obj):
        c = obj.convenio
        return {"id": c.id, "titulo": c.titulo, "tipo": c.tipo_convenio.codigo}

    def get_ipress_detalle(self, obj):
        i = obj.ipress
        return {"id": i.pk, "nombre": i.nombre}


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
        # El ámbito se deriva de la sede docente del campo clínico (UE del convenio); no se pide.
        extra_kwargs = {
            "ambito_geografico_sanitario": {"required": False, "allow_null": True},
        }


class InternshipUpdateSerializer(serializers.ModelSerializer):
    """Solo campos editables del internado (el tutor se cambia con `cambiar-tutor`)."""

    class Meta:
        model = Internship
        fields = [
            "ipress", "observaciones", "fecha_inicio", "fecha_fin",
        ]
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
