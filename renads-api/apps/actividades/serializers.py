"""Serializers del módulo Actividades."""

from rest_framework import serializers

from apps.actividades.models import ActivityStatusHistory, TeachingActivity


class TeachingActivityReadSerializer(serializers.ModelSerializer):
    interno = serializers.StringRelatedField(read_only=True)
    tutor = serializers.StringRelatedField(read_only=True)
    ipress = serializers.CharField(source="ipress.nombre", read_only=True)
    tipo_actividad = serializers.CharField(source="tipo_actividad.nombre", read_only=True)
    estado_actual = serializers.CharField(source="estado_actual.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado_actual.codigo", read_only=True)

    class Meta:
        model = TeachingActivity
        fields = [
            "id", "interno", "internado", "ipress", "rotacion", "tutor", "servicio_area",
            "tipo_actividad", "estado_actual", "estado_codigo", "fecha_actividad",
            "descripcion", "carga_horaria", "creado_por", "creado_en", "actualizado_en",
        ]


class TeachingActivityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingActivity
        fields = [
            "interno", "internado", "ipress", "rotacion", "tutor", "servicio_area",
            "tipo_actividad", "fecha_actividad", "descripcion", "carga_horaria",
        ]


class TeachingActivityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingActivity
        fields = ["descripcion", "carga_horaria", "tipo_actividad", "servicio_area"]
        extra_kwargs = {f: {"required": False} for f in fields}


class ActivityValidationInputSerializer(serializers.Serializer):
    resultado = serializers.ChoiceField(choices=["VALIDADA", "OBSERVADA", "RECHAZADA"])
    comentario = serializers.CharField(required=False, allow_blank=True, default="")


class SubsanarSerializer(serializers.Serializer):
    descripcion = serializers.CharField(required=False, allow_blank=True)
    carga_horaria = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class CambiarEstadoActividadSerializer(serializers.Serializer):
    estado_codigo = serializers.CharField()
    observacion = serializers.CharField(required=False, allow_blank=True, default="")


class ActivityStatusHistorySerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source="estado.nombre", read_only=True)
    estado_codigo = serializers.CharField(source="estado.codigo", read_only=True)

    class Meta:
        model = ActivityStatusHistory
        fields = ["id", "estado", "estado_codigo", "cambiado_por", "cambiado_en", "observacion"]
