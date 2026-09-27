"""Serializers del módulo Internados (bloque núcleo + entradas de flujo)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from django.contrib.contenttypes.models import ContentType

from apps.convenios.models import Convention, Ipress, University, UserEntityProfile
from apps.internados.models import InternshipPeriod
from apps.internados import services
from apps.internados.models import (
    Coordinator,
    CoordinatorSede,
    CoordinatorTutor,
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
    """CRUD de tutores. `universidades` (RN-24): de 1 a 5 universidades por tutor."""

    universidades = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(), many=True,
        help_text="Universidades del tutor (de 1 a 5 — RN-24)",
    )
    # Detalles legibles para el listado (lectura; la escritura sigue por id).
    profesion_detalle = serializers.SerializerMethodField(read_only=True)
    especialidad_detalle = serializers.SerializerMethodField(read_only=True)
    tipo_documento_identidad_detalle = serializers.SerializerMethodField(read_only=True)
    universidades_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Tutor
        fields = "__all__"

    def get_profesion_detalle(self, obj):
        p = obj.profesion
        return {"id": p.id, "nombre": p.nombre} if p else None

    def get_especialidad_detalle(self, obj):
        e = obj.especialidad
        return {"id": e.id, "nombre": e.nombre} if e else None

    def get_tipo_documento_identidad_detalle(self, obj):
        t = obj.tipo_documento_identidad
        return {"id": t.id, "codigo": t.codigo, "nombre": t.nombre} if t else None

    def get_universidades_detalle(self, obj):
        return [{"id": u.id, "nombre": u.nombre, "siglas": u.siglas} for u in obj.universidades.all()]

    def validate_universidades(self, value):
        # B5: usuario Universidad solo puede añadir/quitar sus propias universidades.
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and not user.is_superuser and not user.groups.filter(name="Administrador RENADS").exists():
            ct = ContentType.objects.get_for_model(University)
            ids_ambito = set(
                UserEntityProfile.objects.filter(
                    usuario=user, tipo_contenido=ct, activo=True
                ).values_list("id_objeto", flat=True)
            )
            submitted_ids = {str(u.pk) for u in value}
            if self.instance is not None:
                # Actualización: solo puede añadir/quitar universidades de su propio ámbito.
                current_ids = {str(u.pk) for u in self.instance.universidades.all()}
                cambios = (submitted_ids - current_ids) | (current_ids - submitted_ids)
                for uid in cambios:
                    if uid not in ids_ambito:
                        raise serializers.ValidationError(
                            "Solo puedes añadir o quitar universidades de tu ámbito institucional."
                        )
            else:
                # Alta: todas las universidades enviadas deben estar en su ámbito.
                for u in value:
                    if str(u.pk) not in ids_ambito:
                        raise serializers.ValidationError(
                            "Solo puedes asignar universidades de tu ámbito institucional."
                        )
        # RN-24: fuente única de la regla (1..5 universidades, sin repetidos).
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
# Coordinador de tutores (RN-CRD-01..06)
# ---------------------------------------------------------------------------
class CoordinatorSerializer(serializers.ModelSerializer):
    """CRUD de coordinadores de tutores."""

    tutor = serializers.PrimaryKeyRelatedField(
        queryset=Tutor.objects.all(), allow_null=True, required=False,
        help_text="Tutor vinculado (si el coordinador también es tutor — RN-CRD-02)",
    )
    universidad = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),
        help_text="Universidad a la que pertenece el coordinador",
    )
    tutor_detalle = serializers.SerializerMethodField(read_only=True)
    universidad_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Coordinator
        fields = [
            "id", "tutor", "tutor_detalle", "universidad", "universidad_detalle",
            "tipo_documento_identidad", "numero_documento",
            "nombres", "apellido_paterno", "apellido_materno", "correo", "telefono",
            "numero_colegiatura", "direccion", "ubigeo", "especialidad", "profesion", "activo",
        ]

    def get_tutor_detalle(self, obj):
        if obj.tutor_id is None:
            return None
        t = obj.tutor
        return {"id": t.id, "nombres": t.nombres, "apellido_paterno": t.apellido_paterno}

    def get_universidad_detalle(self, obj):
        u = obj.universidad
        if u is None:
            return None
        return {"id": u.id, "nombre": u.nombre}


class CoordinatorSedeSerializer(serializers.ModelSerializer):
    """Serializer de asignación coordinador ↔ sede docente.

    La universidad ya no se envía en el cuerpo: se deriva del coordinador.
    ``universidad_detalle`` expone la universidad del coordinador en lectura.
    La vista debe hacer ``select_related("coordinador__universidad", "ipress")``
    para evitar consultas N+1.
    """

    coordinador = serializers.PrimaryKeyRelatedField(read_only=True)
    ipress = serializers.PrimaryKeyRelatedField(queryset=Ipress.objects.all())
    universidad_detalle = serializers.SerializerMethodField(read_only=True)
    ipress_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CoordinatorSede
        fields = ["id", "coordinador", "ipress", "universidad_detalle", "ipress_detalle"]

    def get_universidad_detalle(self, obj):
        u = obj.coordinador.universidad
        if u is None:
            return None
        return {"id": u.id, "nombre": u.nombre}

    def get_ipress_detalle(self, obj):
        i = obj.ipress
        return {"id": i.pk, "nombre": i.nombre}


class CoordinatorTutorSerializer(serializers.ModelSerializer):
    """Serializer de tutores asignados a un coordinador por sede (RN-CRD-06)."""

    coordinador_sede = serializers.PrimaryKeyRelatedField(read_only=True)
    tutor = serializers.PrimaryKeyRelatedField(queryset=Tutor.objects.all())
    tutor_detalle = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CoordinatorTutor
        fields = ["id", "coordinador_sede", "tutor", "tutor_detalle"]

    def get_tutor_detalle(self, obj):
        t = obj.tutor
        return {
            "id": t.id,
            "nombres": t.nombres,
            "apellido_paterno": t.apellido_paterno,
            "numero_documento": t.numero_documento,
        }


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

    def validate_tutor(self, tutor):
        """RN-TUT-MAX: un tutor no puede supervisar más de 5 internos activos simultáneamente."""
        if tutor is None:
            return tutor
        # Estados terminados — no cuentan hacia el tope.
        ESTADOS_TERMINADOS = {"CULMINADO", "RETIRADO", "ANULADO"}
        activos = tutor.internos.exclude(
            estado_actual__codigo__in=ESTADOS_TERMINADOS
        ).count()
        from apps.internados.services import MAX_INTERNOS_POR_TUTOR
        if activos >= MAX_INTERNOS_POR_TUTOR:
            raise serializers.ValidationError(
                f"El tutor ya tiene {activos} internos activos (máximo {MAX_INTERNOS_POR_TUTOR})."
            )
        return tutor


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
