"""Services del módulo Actividades: registro, validación y reglas de negocio (RN §5 módulo 3)."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.services import registrar_auditoria
from apps.actividades.models import (
    ActivityStatus,
    ActivityStatusHistory,
    ActivityValidation,
    TeachingActivity,
)

ROTACION_HABILITADA = {"AUTORIZADA", "EN_CURSO"}
VALIDACION_A_ESTADO = {"VALIDADA": "VALIDADA", "OBSERVADA": "OBSERVADA", "RECHAZADA": "RECHAZADA"}


def _estado(codigo: str) -> ActivityStatus:
    try:
        return ActivityStatus.objects.get(codigo=codigo)
    except ActivityStatus.DoesNotExist as exc:
        raise ValidationError(f"Estado de actividad inexistente: {codigo}.") from exc


def _set_estado(actividad: TeachingActivity, codigo: str, usuario, observacion: str = "") -> TeachingActivity:
    estado = _estado(codigo)
    anterior = actividad.estado_actual.codigo if actividad.estado_actual_id else ""
    actividad.estado_actual = estado
    actividad.save(update_fields=["estado_actual", "actualizado_en"])
    ActivityStatusHistory.objects.create(
        actividad=actividad, estado=estado, cambiado_por=usuario, observacion=observacion
    )
    registrar_auditoria(
        usuario, "CAMBIO_ESTADO", actividad,
        nombre_campo="estado_actual", valor_anterior=anterior, valor_nuevo=codigo,
    )
    return actividad


@transaction.atomic
def registrar_actividad(*, datos: dict, usuario) -> TeachingActivity:
    internado = datos["internado"]
    fecha = datos["fecha_actividad"]
    rotacion = datos.get("rotacion")

    # RN-1: solo internados activos.
    if not internado.estado_actual_id or internado.estado_actual.codigo != "ACTIVO":
        raise ValidationError({"internado": "El internado debe estar activo."})
    # RN-2: la actividad debe estar dentro del periodo del internado.
    if fecha < internado.fecha_inicio or fecha > internado.fecha_fin:
        raise ValidationError({"fecha_actividad": "Fuera del periodo del internado."})
    # RN-3/4: si hay rotación, debe pertenecer al internado y estar autorizada/en curso.
    if rotacion is not None:
        if rotacion.internado_id != internado.id:
            raise ValidationError({"rotacion": "La rotación no pertenece al internado."})
        if rotacion.estado_actual.codigo not in ROTACION_HABILITADA:
            raise ValidationError({"rotacion": "La rotación debe estar autorizada o en curso."})
    # RN-9: evitar duplicados evidentes.
    duplicado = TeachingActivity.objects.filter(
        interno=datos["interno"], fecha_actividad=fecha,
        ipress=datos["ipress"], servicio_area=datos["servicio_area"],
    ).exists()
    if duplicado:
        raise ValidationError("Ya existe una actividad para ese interno, fecha, sede y servicio.")

    estado_inicial = _estado("REGISTRADA")
    actividad = TeachingActivity.objects.create(
        interno=datos["interno"],
        internado=internado,
        ipress=datos["ipress"],
        rotacion=rotacion,
        tutor=datos["tutor"],
        servicio_area=datos["servicio_area"],
        tipo_actividad=datos["tipo_actividad"],
        estado_actual=estado_inicial,
        fecha_actividad=fecha,
        descripcion=datos.get("descripcion", ""),
        carga_horaria=datos.get("carga_horaria"),
        creado_por=usuario,
    )
    ActivityStatusHistory.objects.create(
        actividad=actividad, estado=estado_inicial, cambiado_por=usuario
    )
    registrar_auditoria(usuario, "CREAR", actividad)
    return actividad


@transaction.atomic
def actualizar_actividad(*, actividad: TeachingActivity, datos: dict, usuario) -> TeachingActivity:
    """RN-8: una actividad validada no se modifica."""
    if actividad.estado_actual_id and actividad.estado_actual.codigo == "VALIDADA":
        raise ValidationError("Una actividad validada no puede modificarse.")
    for campo in ("descripcion", "carga_horaria", "tipo_actividad", "servicio_area"):
        if campo in datos:
            setattr(actividad, campo, datos[campo])
    actividad.save()
    registrar_auditoria(usuario, "ACTUALIZAR", actividad)
    return actividad


@transaction.atomic
def validar_actividad(*, actividad: TeachingActivity, datos: dict, usuario) -> ActivityValidation:
    validacion = ActivityValidation.objects.create(
        actividad=actividad,
        resultado=datos["resultado"],
        comentario=datos.get("comentario", ""),
        validado_por=usuario,
        fecha_validacion=timezone.now(),
    )
    registrar_auditoria(usuario, "CREAR", validacion)
    _set_estado(actividad, VALIDACION_A_ESTADO[validacion.resultado], usuario)
    return validacion


@transaction.atomic
def subsanar_actividad(*, actividad: TeachingActivity, datos: dict, usuario) -> TeachingActivity:
    """RN-7: solo las actividades observadas pueden subsanarse."""
    if not actividad.estado_actual_id or actividad.estado_actual.codigo != "OBSERVADA":
        raise ValidationError("Solo se pueden subsanar actividades observadas.")
    for campo in ("descripcion", "carga_horaria"):
        if campo in datos:
            setattr(actividad, campo, datos[campo])
    actividad.save()
    _set_estado(actividad, "SUBSANADA", usuario)
    return actividad


@transaction.atomic
def cambiar_estado_actividad(*, actividad: TeachingActivity, nuevo_estado_codigo: str, usuario, observacion: str = "") -> TeachingActivity:
    return _set_estado(actividad, nuevo_estado_codigo, usuario, observacion)
