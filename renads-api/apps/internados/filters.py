"""FilterSets del módulo Internados."""

from django_filters import rest_framework as filters

from apps.internados.models import Internship, Rotation


class InternshipFilter(filters.FilterSet):
    fecha_inicio_desde = filters.DateFilter(field_name="fecha_inicio", lookup_expr="gte")
    fecha_inicio_hasta = filters.DateFilter(field_name="fecha_inicio", lookup_expr="lte")
    fecha_fin_desde = filters.DateFilter(field_name="fecha_fin", lookup_expr="gte")
    fecha_fin_hasta = filters.DateFilter(field_name="fecha_fin", lookup_expr="lte")

    class Meta:
        model = Internship
        fields = {
            "convenio": ["exact"],
            "ipress": ["exact"],
            "tutor": ["exact"],
            "estado_actual": ["exact"],
            "ambito_geografico_sanitario": ["exact"],
            "interno": ["exact"],
        }


class RotationFilter(filters.FilterSet):
    class Meta:
        model = Rotation
        fields = {
            "internado": ["exact"],
            "estado_actual": ["exact"],
            "ipress_origen": ["exact"],
            "ipress_destino": ["exact"],
            "servicio_area": ["exact"],
        }
