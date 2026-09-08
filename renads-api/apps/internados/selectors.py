"""Selectors de lectura del módulo Internados (incluye alcance institucional)."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import Ipress, University
from apps.internados.models import (
    Student,
    Internship,
    InternshipStatusHistory,
    Rotation,
    RotationStatusHistory,
    TutorHistory,
)


def estudiantes_visibles(usuario) -> QuerySet[Student]:
    """Estudiantes dentro del ámbito del usuario (RNF-SEG-04).

    - Superusuario: todos los estudiantes.
    - Usuario con perfil de universidad (p. ej. rol ``Universidad``): los
      estudiantes de sus universidades.
    - Interno (RN-22): únicamente su propio ``Student`` (perfil sobre ``Student``).
    - Sin perfil relevante: ninguno.
    """
    qs = Student.objects.select_related("universidad", "carrera_profesional")
    if usuario.is_superuser:
        return qs
    refs = entidades_del_usuario(usuario)
    ct_uni = ContentType.objects.get_for_model(University).id
    ct_student = ContentType.objects.get_for_model(Student).id
    universidades = [oid for (tc, oid) in refs if tc == ct_uni]
    propios = [oid for (tc, oid) in refs if tc == ct_student]
    if universidades:
        return qs.filter(universidad_id__in=universidades)
    if propios:
        # Interno: solo su propio estudiante (lectura de sus datos).
        return qs.filter(id__in=propios)
    return qs.none()


def internados_visibles(usuario) -> QuerySet[Internship]:
    """Internados dentro del alcance institucional: universidad del estudiante o sede (IPRESS).

    - Superusuario: todos.
    - Universidad/sede: internados de sus universidades o sedes (IPRESS).
    - Interno (RN-22): únicamente los internados de su propio ``Student`` (perfil
      sobre ``Student``) — habilita el adjunto de sus declaraciones juradas.
    - Sin perfiles relevantes → ninguno.
    """
    qs = Internship.objects.select_related(
        "estudiante", "convenio", "campo_clinico", "ipress", "tutor", "estado_actual"
    )
    if usuario.is_superuser:
        return qs
    refs = entidades_del_usuario(usuario)
    if not refs:
        return qs.none()
    ct_uni = ContentType.objects.get_for_model(University).id
    ct_ip = ContentType.objects.get_for_model(Ipress).id
    ct_student = ContentType.objects.get_for_model(Student).id
    # `universidades`/`propios` comparan contra columnas enteras → castear a int; `sedes`
    # compara contra `ipress_id` (texto tras el refactor de la PK de Ipress) → permanece str.
    universidades = [oid for (tc, oid) in refs if tc == ct_uni]
    sedes = [oid for (tc, oid) in refs if tc == ct_ip]
    propios = [oid for (tc, oid) in refs if tc == ct_student]
    if not universidades and not sedes and not propios:
        return qs.none()
    condicion = Q()
    if universidades:
        condicion |= Q(estudiante__universidad_id__in=[int(x) for x in universidades])
    if sedes:
        condicion |= Q(ipress_id__in=sedes)
    if propios:
        condicion |= Q(estudiante_id__in=[int(x) for x in propios])
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
