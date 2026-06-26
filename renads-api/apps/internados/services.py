"""Services del módulo Internados: casos de uso de escritura y reglas de negocio (RN).

Toda escritura en `transaction.atomic()`, con auditoría en `bitacora_auditoria` y
registro en el historial de estado correspondiente. Ver §6 del módulo 2.
"""

import datetime

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.common.services import registrar_auditoria
from apps.internados.models import (
    Internship,
    InternshipStatus,
    InternshipStatusHistory,
    Rotation,
    RotationAuthorization,
    RotationStatus,
    RotationStatusHistory,
    TutorHistory,
)

# Estados del Convenio Específico que habilitan registrar internados (RN-2/3).
ESTADOS_CONVENIO_VIGENTE = {"VIGENTE", "PUBLICADO", "SUSCRITO"}
MAX_ROTACIONES = 4  # RN-9


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sumar_anios(fecha: datetime.date, anios: int) -> datetime.date:
    try:
        return fecha.replace(year=fecha.year + anios)
    except ValueError:
        return fecha.replace(year=fecha.year + anios, day=28)


def _estado_internado(codigo: str) -> InternshipStatus:
    try:
        return InternshipStatus.objects.get(codigo=codigo)
    except InternshipStatus.DoesNotExist as exc:
        raise ValidationError(f"Estado de internado inexistente: {codigo}.") from exc


def _estado_rotacion(codigo: str) -> RotationStatus:
    try:
        return RotationStatus.objects.get(codigo=codigo)
    except RotationStatus.DoesNotExist as exc:
        raise ValidationError(f"Estado de rotación inexistente: {codigo}.") from exc


def _set_estado_internado(internado: Internship, codigo: str, usuario, observacion: str = "") -> Internship:
    estado = _estado_internado(codigo)
    anterior = internado.estado_actual.codigo if internado.estado_actual_id else ""
    internado.estado_actual = estado
    internado.save(update_fields=["estado_actual", "actualizado_en"])
    InternshipStatusHistory.objects.create(
        internado=internado, estado=estado, cambiado_por=usuario, observacion=observacion
    )
    registrar_auditoria(
        usuario, "CAMBIO_ESTADO", internado,
        nombre_campo="estado_actual", valor_anterior=anterior, valor_nuevo=codigo,
    )
    return internado


def _set_estado_rotacion(rotacion: Rotation, codigo: str, usuario, observacion: str = "") -> Rotation:
    estado = _estado_rotacion(codigo)
    anterior = rotacion.estado_actual.codigo if rotacion.estado_actual_id else ""
    rotacion.estado_actual = estado
    rotacion.save(update_fields=["estado_actual"])
    RotationStatusHistory.objects.create(
        rotacion=rotacion, estado=estado, cambiado_por=usuario, observacion=observacion
    )
    registrar_auditoria(
        usuario, "CAMBIO_ESTADO", rotacion,
        nombre_campo="estado_actual", valor_anterior=anterior, valor_nuevo=codigo,
    )
    return rotacion


# ---------------------------------------------------------------------------
# Internado
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_internado(*, datos: dict, usuario) -> Internship:
    convenio = datos["convenio"]
    campo_clinico = datos["campo_clinico"]
    fecha_inicio = datos["fecha_inicio"]
    fecha_fin = datos["fecha_fin"]

    # RN-4: no se permite sobre Convenio Marco.
    if convenio.tipo_convenio.codigo != "ESPECIFICO":
        raise ValidationError({"convenio": "El internado requiere un Convenio Específico."})
    # RN-2/3: convenio vigente.
    if not convenio.estado_actual_id or convenio.estado_actual.codigo not in ESTADOS_CONVENIO_VIGENTE:
        raise ValidationError({"convenio": "El Convenio Específico debe estar vigente."})
    # El campo clínico debe pertenecer al convenio.
    if campo_clinico.convenio_id != convenio.id:
        raise ValidationError({"campo_clinico": "El campo clínico no pertenece al convenio indicado."})
    # RN-13: no exceder los campos clínicos autorizados.
    usados = Internship.objects.filter(campo_clinico=campo_clinico).count()
    if usados >= campo_clinico.cantidad_maxima:
        raise ValidationError({"campo_clinico": "Se alcanzó el máximo de campos clínicos autorizados."})
    # RN-6: duración máxima de un año.
    if fecha_fin > _sumar_anios(fecha_inicio, 1):
        raise ValidationError({"fecha_fin": "El internado no puede durar más de un año."})
    if fecha_fin < fecha_inicio:
        raise ValidationError({"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."})
    # Coherencia de ámbito con el campo clínico.
    if datos["ambito_geografico_sanitario"].id != campo_clinico.ambito_geografico_sanitario_id:
        raise ValidationError(
            {"ambito_geografico_sanitario": "Debe coincidir con el ámbito del campo clínico."}
        )

    estado_inicial = _estado_internado("REGISTRADO")
    internado = Internship.objects.create(
        interno=datos["interno"],
        convenio=convenio,
        campo_clinico=campo_clinico,
        ipress=datos["ipress"],
        tutor=datos["tutor"],
        ambito_geografico_sanitario=datos["ambito_geografico_sanitario"],
        estado_actual=estado_inicial,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        observaciones=datos.get("observaciones", ""),
        creado_por=usuario,
    )
    InternshipStatusHistory.objects.create(
        internado=internado, estado=estado_inicial, cambiado_por=usuario
    )
    registrar_auditoria(usuario, "CREAR", internado)
    return internado


@transaction.atomic
def actualizar_internado(*, internado: Internship, datos: dict, usuario) -> Internship:
    """Actualiza campos editables (no el tutor: usar `cambiar_tutor`; ni el estado)."""
    if "fecha_inicio" in datos or "fecha_fin" in datos:
        inicio = datos.get("fecha_inicio", internado.fecha_inicio)
        fin = datos.get("fecha_fin", internado.fecha_fin)
        if fin > _sumar_anios(inicio, 1) or fin < inicio:
            raise ValidationError({"fecha_fin": "Periodo inválido (máximo un año)."})
        internado.fecha_inicio, internado.fecha_fin = inicio, fin
    if "ipress" in datos:
        nueva_ipress = datos["ipress"]
        if nueva_ipress.ambito_geografico_sanitario_id != internado.ambito_geografico_sanitario_id:
            raise ValidationError(
                {"ipress": "La sede debe pertenecer al ámbito geográfico del internado."}
            )
        internado.ipress = nueva_ipress
    if "observaciones" in datos:
        internado.observaciones = datos["observaciones"]
    internado.save()
    registrar_auditoria(usuario, "ACTUALIZAR", internado)
    return internado


@transaction.atomic
def cambiar_estado_internado(*, internado: Internship, nuevo_estado_codigo: str, usuario, observacion: str = "") -> Internship:
    return _set_estado_internado(internado, nuevo_estado_codigo, usuario, observacion)


@transaction.atomic
def cambiar_tutor(*, internado: Internship, datos: dict, usuario) -> Internship:
    """RN-14: registra el cambio de tutor con fecha, motivo y responsable."""
    TutorHistory.objects.create(
        internado=internado,
        tutor=datos["tutor"],
        fecha_cambio=datos["fecha_cambio"],
        motivo=datos["motivo"],
        responsable=usuario,
    )
    anterior = internado.tutor_id
    internado.tutor = datos["tutor"]
    internado.save(update_fields=["tutor", "actualizado_en"])
    registrar_auditoria(
        usuario, "ACTUALIZAR", internado,
        nombre_campo="tutor", valor_anterior=anterior, valor_nuevo=internado.tutor_id,
    )
    return internado


# ---------------------------------------------------------------------------
# Rotación
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_rotacion(*, internado: Internship, datos: dict, usuario) -> Rotation:
    origen = datos["ipress_origen"]
    destino = datos["ipress_destino"]
    fecha_inicio = datos["fecha_inicio"]
    fecha_fin = datos["fecha_fin"]

    # RN-8: ambas sedes en el mismo ámbito geográfico sanitario del internado.
    ambito = internado.ambito_geografico_sanitario_id
    if origen.ambito_geografico_sanitario_id != ambito or destino.ambito_geografico_sanitario_id != ambito:
        raise ValidationError("Las sedes deben pertenecer al ámbito geográfico sanitario del internado.")
    # RN-12: fechas dentro del periodo del internado.
    if fecha_inicio < internado.fecha_inicio or fecha_fin > internado.fecha_fin or fecha_fin < fecha_inicio:
        raise ValidationError("Las fechas de la rotación deben estar dentro del periodo del internado.")
    # RN-9: máximo 4 rotaciones por interno.
    actuales = internado.rotaciones.count()
    if actuales >= MAX_ROTACIONES:
        raise ValidationError(f"El interno no puede exceder {MAX_ROTACIONES} rotaciones.")

    estado_inicial = _estado_rotacion("SOLICITADA")
    rotacion = Rotation.objects.create(
        internado=internado,
        numero_rotacion=actuales + 1,
        ipress_origen=origen,
        ipress_destino=destino,
        servicio_area=datos["servicio_area"],
        estado_actual=estado_inicial,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        observaciones=datos.get("observaciones", ""),
        creado_por=usuario,
    )
    RotationStatusHistory.objects.create(
        rotacion=rotacion, estado=estado_inicial, cambiado_por=usuario
    )
    registrar_auditoria(usuario, "CREAR", rotacion)
    return rotacion


@transaction.atomic
def autorizar_rotacion(*, rotacion: Rotation, datos: dict, usuario) -> RotationAuthorization:
    """RN-10: solo una autoridad suscrita (firmante) del Convenio Específico autoriza."""
    participante = datos["participante_convenio"]
    if participante.convenio_id != rotacion.internado.convenio_id or not participante.es_firmante:
        raise ValidationError(
            {"participante_convenio": "Debe ser una autoridad firmante del Convenio Específico del internado."}
        )
    autorizacion = RotationAuthorization.objects.create(
        rotacion=rotacion,
        participante_convenio=participante,
        resultado=datos["resultado"],
        fecha_autorizacion=datos["fecha_autorizacion"],
        observaciones=datos.get("observaciones", ""),
        autorizado_por=usuario,
    )
    registrar_auditoria(usuario, "CREAR", autorizacion)
    mapa = {"APROBADO": "AUTORIZADA", "OBSERVADO": "OBSERVADA", "RECHAZADO": "RECHAZADA"}
    _set_estado_rotacion(rotacion, mapa[autorizacion.resultado], usuario)
    return autorizacion


@transaction.atomic
def iniciar_rotacion(*, rotacion: Rotation, usuario) -> Rotation:
    """RN-11: no se puede iniciar una rotación sin autorización aprobada."""
    if not rotacion.autorizaciones.filter(resultado="APROBADO").exists():
        raise ValidationError("La rotación no puede iniciar sin una autorización aprobada.")
    return _set_estado_rotacion(rotacion, "EN_CURSO", usuario)


@transaction.atomic
def cambiar_estado_rotacion(*, rotacion: Rotation, nuevo_estado_codigo: str, usuario, observacion: str = "") -> Rotation:
    return _set_estado_rotacion(rotacion, nuevo_estado_codigo, usuario, observacion)
