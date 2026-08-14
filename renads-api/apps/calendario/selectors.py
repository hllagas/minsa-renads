"""Selectores del Calendario: fuente única de la semántica temporal de habilitación.

Funciones puras (sin efectos) que, dado un instante `now`, calculan qué
`ContentType` están gobernados por alguna actividad controladora y cuáles
tienen una ventana vigente. Consumidas por el permiso `IsModuleEnabled`
(escritura) y por `MeSerializer` (exposición al frontend). La semántica entre
ventanas del mismo ContentType es **OR**: basta una ventana vigente para
habilitar.
"""

from django.db.models import Q

from apps.calendario.models import CalendarActivity


def content_types_controlados(now) -> set[int]:
    """Conjunto de `content_type_id` gobernados por alguna actividad controladora.

    Define "quién está gobernado": ContentTypes referenciados por al menos una
    `CalendarActivity` con `controla_acceso=True` y `activo=True`. No filtra por
    fechas.
    """
    ids = (
        CalendarActivity.objects.filter(controla_acceso=True, activo=True)
        .values_list("content_types__id", flat=True)
        .distinct()
    )
    return {ct_id for ct_id in ids if ct_id is not None}


def content_types_habilitados(now) -> set[int]:
    """Subconjunto de los controlados con ≥1 ventana vigente en `now`.

    Un ContentType está habilitado si existe una `CalendarActivity` con
    `controla_acceso=True`, `activo=True`, `fecha_inicio <= now.date()` y
    (`fecha_fin` NULL o `fecha_fin >= now.date()`). NULL = ventana abierta.
    """
    hoy = now.date()
    ids = (
        CalendarActivity.objects.filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy),
            controla_acceso=True,
            activo=True,
            fecha_inicio__lte=hoy,
        )
        .values_list("content_types__id", flat=True)
        .distinct()
    )
    return {ct_id for ct_id in ids if ct_id is not None}


def esta_habilitado(ct_id: int, now) -> bool:
    """Indica si el ContentType `ct_id` admite escritura en `now`.

    True si el módulo no está gobernado (pass-through) o si tiene una ventana
    vigente. False si está gobernado y sin ventana vigente.
    """
    if ct_id not in content_types_controlados(now):
        return True
    return ct_id in content_types_habilitados(now)
