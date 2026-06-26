"""Selectors de lectura del módulo Internados (incluye alcance institucional)."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import Ipress, University
from apps.internados.models import (
    Intern,
    Internship,
    InternshipStatusHistory,
    Rotation,
    RotationStatusHistory,
    TutorHistory,
)


def interns_visibles(usuario) -> QuerySet[Intern]:
    """Internos de las universidades dentro del ámbito del usuario (RNF-SEG-04)."""
    qs = Intern.objects.select_related("universidad", "carrera_profesional", "especialidad")
    if usuario.is_superuser:
        return qs
    refs = entidades_del_usuario(usuario)
    ct_uni = ContentType.objects.get_for_model(University).id
    universidades = [oid for (tc, oid) in refs if tc == ct_uni]
    return qs.filter(universidad_id__in=universidades) if universidades else qs.none()


def internados_visibles(usuario) -> QuerySet[Internship]:
    """Internados dentro del alcance institucional: universidad del interno o sede (IPRESS).

    Superusuario ve todo. Sin perfiles relevantes → ninguno.
    """
    qs = Internship.objects.select_related(
        "interno", "convenio", "campo_clinico", "ipress", "tutor", "estado_actual"
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


def rotaciones_de(internado: Internship) -> QuerySet[Rotation]:
    return internado.rotaciones.select_related(
        "ipress_origen", "ipress_destino", "servicio_area", "estado_actual"
    )


def rotaciones_count(internado: Internship) -> int:
    return internado.rotaciones.count()


def historial_internado(internado: Internship) -> QuerySet[InternshipStatusHistory]:
    return internado.historial_estados.select_related("estado", "cambiado_por").order_by("cambiado_en")


def historial_tutor(internado: Internship) -> QuerySet[TutorHistory]:
    return internado.historial_tutores.select_related("tutor", "responsable").order_by("creado_en")


def historial_rotacion(rotacion: Rotation) -> QuerySet[RotationStatusHistory]:
    return rotacion.historial_estados.select_related("estado", "cambiado_por").order_by("cambiado_en")
