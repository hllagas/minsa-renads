"""Selectors de lectura del módulo Actividades (incluye alcance institucional)."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import Ipress, University
from apps.actividades.models import ActivityStatusHistory, TeachingActivity


def actividades_visibles(usuario) -> QuerySet[TeachingActivity]:
    """Actividades dentro del ámbito del usuario: universidad del interno o sede (IPRESS)."""
    qs = TeachingActivity.objects.select_related(
        "interno", "internado", "ipress", "tutor", "tipo_actividad", "estado_actual", "rotacion"
    )
    if usuario.is_superuser:
        return qs
    refs = entidades_del_usuario(usuario)
    if not refs:
        return qs.none()
    ct_uni = ContentType.objects.get_for_model(University).id
    ct_ip = ContentType.objects.get_for_model(Ipress).id
    universidades = [oid for (tc, oid) in refs if tc == ct_uni]
    sedes = [oid for (tc, oid) in refs if tc == ct_ip]
    if not universidades and not sedes:
        return qs.none()
    condicion = Q()
    if universidades:
        condicion |= Q(interno__universidad_id__in=universidades)
    if sedes:
        condicion |= Q(ipress_id__in=sedes)
    return qs.filter(condicion)


def historial_actividad(actividad: TeachingActivity) -> QuerySet[ActivityStatusHistory]:
    return actividad.historial_estados.select_related("estado", "cambiado_por").order_by("cambiado_en")
