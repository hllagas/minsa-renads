"""FilterSet de la feature Calendario (`calendar-activities`)."""

from django.contrib.contenttypes.models import ContentType
from django_filters import rest_framework as filters

from apps.calendario.models import CalendarActivity


class CalendarActivityFilter(filters.FilterSet):
    """Filtros de actividades de calendario.

    - `controla_acceso` / `activo`: booleanos exactos.
    - `content_types`: por id de ContentType relacionado; admite múltiples valores
      (p. ej. `?content_types=5&content_types=8`).
    - `fecha_desde` / `fecha_hasta`: acotan por la fecha de inicio de la ventana
      (`fecha_inicio >= fecha_desde`, `fecha_inicio <= fecha_hasta`).
    - `fecha_fin_desde` / `fecha_fin_hasta`: acotan por la fecha de fin de la ventana.
    """

    content_types = filters.ModelMultipleChoiceFilter(
        field_name="content_types",
        queryset=ContentType.objects.all(),
    )
    fecha_desde = filters.DateFilter(field_name="fecha_inicio", lookup_expr="gte")
    fecha_hasta = filters.DateFilter(field_name="fecha_inicio", lookup_expr="lte")
    fecha_fin_desde = filters.DateFilter(field_name="fecha_fin", lookup_expr="gte")
    fecha_fin_hasta = filters.DateFilter(field_name="fecha_fin", lookup_expr="lte")

    class Meta:
        model = CalendarActivity
        fields = ["controla_acceso", "activo", "content_types"]
