"""FilterSets del módulo Actividades."""

from django_filters import rest_framework as filters

from apps.actividades.models import TeachingActivity


class TeachingActivityFilter(filters.FilterSet):
    fecha_desde = filters.DateFilter(field_name="fecha_actividad", lookup_expr="gte")
    fecha_hasta = filters.DateFilter(field_name="fecha_actividad", lookup_expr="lte")

    class Meta:
        model = TeachingActivity
        fields = {
            "interno": ["exact"],
            "internado": ["exact"],
            "ipress": ["exact"],
            "tutor": ["exact"],
            "rotacion": ["exact"],
            "tipo_actividad": ["exact"],
            "estado_actual": ["exact"],
        }
