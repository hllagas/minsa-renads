"""Serializers de la feature Calendario: lectura (con detalles) y escritura."""

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from apps.calendario.models import CalendarActivity


def _content_type_detalle(ct: ContentType) -> dict:
    """Serializa un ContentType con el mismo shape que el endpoint `content-types`."""
    modelo = ct.model_class()
    verbose_name = str(modelo._meta.verbose_name) if modelo is not None else ct.name
    return {
        "id": ct.id,
        "app_label": ct.app_label,
        "model": ct.model,
        "verbose_name": verbose_name,
    }


class CalendarActivityReadSerializer(serializers.ModelSerializer):
    """Lectura de actividades de calendario: campos legibles + detalles de M2M."""

    content_types_detalle = serializers.SerializerMethodField()

    class Meta:
        model = CalendarActivity
        fields = [
            "id",
            "nombre",
            "detalle",
            "numero_orden",
            "fecha_inicio",
            "fecha_fin",
            "controla_acceso",
            "activo",
            "responsables",
            "content_types",
            "content_types_detalle",
            "creado_en",
            "creado_por",
            "actualizado_en",
            "actualizado_por",
        ]
        read_only_fields = fields

    def get_content_types_detalle(self, obj) -> list[dict]:
        return [_content_type_detalle(ct) for ct in obj.content_types.all()]


class CalendarActivityWriteSerializer(serializers.ModelSerializer):
    """Escritura de actividades de calendario.

    Recibe `responsables` como texto libre y `content_types` por id. Los campos de
    auditoría los fija el ViewSet (`creado_por`/`actualizado_por`); las marcas de
    tiempo son automáticas.
    """

    content_types = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ContentType.objects.all(), required=False
    )

    class Meta:
        model = CalendarActivity
        fields = [
            "id",
            "nombre",
            "detalle",
            "numero_orden",
            "fecha_inicio",
            "fecha_fin",
            "controla_acceso",
            "activo",
            "responsables",
            "content_types",
        ]

    def validate(self, attrs):
        """RN: si `fecha_fin` no es nula, debe ser >= `fecha_inicio`."""
        fecha_inicio = attrs.get(
            "fecha_inicio", getattr(self.instance, "fecha_inicio", None)
        )
        fecha_fin = attrs.get("fecha_fin", getattr(self.instance, "fecha_fin", None))
        if fecha_fin is not None and fecha_inicio is not None and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."}
            )
        return attrs
