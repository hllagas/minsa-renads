"""FilterSets del módulo Internados."""

from django_filters import rest_framework as filters

from apps.internados.models import Internship, Rotation, Student


class StudentFilter(filters.FilterSet):
    """Filtros de estudiantes. `nivel_academico` filtra por el nivel de la carrera (RN-19):
    el estudiante no persiste el nivel; deriva de `carrera_profesional.nivel_academico`."""

    nivel_academico = filters.NumberFilter(
        field_name="carrera_profesional__nivel_academico"
    )

    class Meta:
        model = Student
        fields = {
            "universidad": ["exact"],
            "carrera_profesional": ["exact"],
            "periodo_internado": ["exact"],
            "especialidad": ["exact"],
            "numero_documento": ["exact"],
            "activo": ["exact"],
        }


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
            "estudiante": ["exact"],
        }


class RotationFilter(filters.FilterSet):
    class Meta:
        model = Rotation
        fields = {
            "interno": ["exact"],
            "estado_actual": ["exact"],
            "ipress_origen": ["exact"],
            "ipress_destino": ["exact"],
            "servicio_area": ["exact"],
        }
