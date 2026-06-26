"""FilterSets del módulo Convenios."""

from django_filters import rest_framework as filters

from apps.convenios.models import ClinicalField, Convention


class ConventionFilter(filters.FilterSet):
    fecha_solicitud_desde = filters.DateFilter(field_name="fecha_solicitud", lookup_expr="gte")
    fecha_solicitud_hasta = filters.DateFilter(field_name="fecha_solicitud", lookup_expr="lte")
    fecha_fin_desde = filters.DateFilter(field_name="fecha_fin", lookup_expr="gte")
    fecha_fin_hasta = filters.DateFilter(field_name="fecha_fin", lookup_expr="lte")

    class Meta:
        model = Convention
        fields = {
            "tipo_convenio": ["exact"],
            "estado_actual": ["exact"],
            "convenio_marco": ["exact"],
            "solicitante_tipo_contenido": ["exact"],
            "solicitante_id_objeto": ["exact"],
        }


class ClinicalFieldFilter(filters.FilterSet):
    class Meta:
        model = ClinicalField
        fields = {
            "convenio": ["exact"],
            "ipress": ["exact"],
            "carrera_profesional": ["exact"],
            "especialidad": ["exact"],
            "ambito_geografico_sanitario": ["exact"],
        }
