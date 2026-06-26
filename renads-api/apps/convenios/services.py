"""Services del módulo Convenios: casos de uso de escritura y reglas de negocio (RN).

Toda escritura corre en `transaction.atomic()`, registra auditoría en
`bitacora_auditoria` y, si cambia el estado del convenio, en
`historial_estado_convenio`. Ver `docs/db_schema_modulo_01_convenios.md` y §6 del módulo.
"""

import datetime

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.common.services import registrar_auditoria
from apps.convenios.models import (
    ClinicalField,
    ConapresOpinion,
    Convention,
    ConventionParticipant,
    ConventionStatus,
    ConventionStatusHistory,
    LegalOpinion,
    Publication,
    Signature,
    TechnicalEvaluation,
)

# Estados que consideran "vigente" un Convenio Marco para soportar un Específico (RN-3).
ESTADOS_VIGENTES = {"VIGENTE", "PUBLICADO", "SUSCRITO"}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _sumar_anios(fecha: datetime.date, anios: int) -> datetime.date:
    try:
        return fecha.replace(year=fecha.year + anios)
    except ValueError:  # 29 de febrero en año no bisiesto
        return fecha.replace(year=fecha.year + anios, day=28)


def _obtener_estado(codigo: str) -> ConventionStatus:
    try:
        return ConventionStatus.objects.get(codigo=codigo)
    except ConventionStatus.DoesNotExist as exc:
        raise ValidationError(f"Estado de convenio inexistente: {codigo}.") from exc


def _set_estado(convenio: Convention, codigo: str, usuario, observacion: str = "") -> Convention:
    estado = _obtener_estado(codigo)
    if estado.aplica_a == "ESPECIFICO" and convenio.tipo_convenio.codigo != "ESPECIFICO":
        raise ValidationError(f"El estado {codigo} solo aplica a Convenios Específicos.")
    anterior = convenio.estado_actual.codigo if convenio.estado_actual_id else ""
    convenio.estado_actual = estado
    convenio.save(update_fields=["estado_actual", "actualizado_en"])
    ConventionStatusHistory.objects.create(
        convenio=convenio, estado=estado, cambiado_por=usuario, observacion=observacion
    )
    registrar_auditoria(
        usuario, "CAMBIO_ESTADO", convenio,
        nombre_campo="estado_actual", valor_anterior=anterior, valor_nuevo=codigo,
    )
    return convenio


def _tiene_observaciones_pendientes(convenio: Convention) -> bool:
    """RN-9: hay observaciones técnicas/normativas/jurídicas sin subsanar."""
    te = convenio.evaluaciones_tecnicas.order_by("-creado_en").first()
    if te and te.resultado == "OBSERVADO":
        return True
    co = convenio.opiniones_conapres.order_by("-creado_en").first()
    if co and co.resultado_opinion == "OBSERVADO":
        return True
    lo = convenio.opiniones_juridicas.order_by("-creado_en").first()
    if lo and lo.resultado_opinion == "OBSERVADO":
        return True
    return False


def _exigir_especifico(convenio: Convention, actividad: str) -> None:
    if convenio.tipo_convenio.codigo != "ESPECIFICO":
        raise ValidationError(f"{actividad} solo aplica a Convenios Específicos.")


# ---------------------------------------------------------------------------
# Casos de uso
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_convenio(*, datos: dict, usuario) -> Convention:
    """Registra un convenio. RN-3: el Específico requiere un Marco vigente."""
    tipo = datos["tipo_convenio"]
    marco = datos.get("convenio_marco")

    if tipo.codigo == "ESPECIFICO":
        if marco is None:
            raise ValidationError({"convenio_marco": "Requerido para un Convenio Específico."})
        if not marco.estado_actual_id or marco.estado_actual.codigo not in ESTADOS_VIGENTES:
            raise ValidationError({"convenio_marco": "El Convenio Marco debe estar vigente."})
    elif marco is not None:
        raise ValidationError({"convenio_marco": "Un Convenio Marco no depende de otro convenio."})

    fecha_inicio = datos.get("fecha_inicio")
    fecha_fin = datos.get("fecha_fin")
    if fecha_inicio and not fecha_fin and tipo.anios_vigencia:
        fecha_fin = _sumar_anios(fecha_inicio, tipo.anios_vigencia)

    estado_inicial = _obtener_estado("SOLICITUD_REGISTRADA")
    convenio = Convention.objects.create(
        tipo_convenio=tipo,
        convenio_marco=marco,
        plantilla=datos.get("plantilla"),
        codigo=datos.get("codigo", ""),
        titulo=datos["titulo"],
        solicitante_tipo_contenido=datos["solicitante_tipo_contenido"],
        solicitante_id_objeto=datos["solicitante_id_objeto"],
        estado_actual=estado_inicial,
        fecha_solicitud=datos["fecha_solicitud"],
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        max_campos_clinicos=datos.get("max_campos_clinicos"),
        creado_por=usuario,
    )
    ConventionStatusHistory.objects.create(
        convenio=convenio, estado=estado_inicial, cambiado_por=usuario
    )
    registrar_auditoria(usuario, "CREAR", convenio)
    return convenio


@transaction.atomic
def actualizar_convenio(*, convenio: Convention, datos: dict, usuario) -> Convention:
    """Actualiza campos editables del convenio (no el estado: usar `cambiar_estado`)."""
    editables = ["codigo", "titulo", "plantilla", "fecha_inicio", "fecha_fin", "max_campos_clinicos"]
    for campo in editables:
        if campo in datos:
            setattr(convenio, campo, datos[campo])
    convenio.save()
    registrar_auditoria(usuario, "ACTUALIZAR", convenio)
    return convenio


@transaction.atomic
def cambiar_estado(*, convenio: Convention, nuevo_estado_codigo: str, usuario, observacion: str = "") -> Convention:
    return _set_estado(convenio, nuevo_estado_codigo, usuario, observacion)


@transaction.atomic
def registrar_evaluacion_tecnica(*, convenio: Convention, datos: dict, usuario) -> TechnicalEvaluation:
    evaluacion = TechnicalEvaluation.objects.create(convenio=convenio, evaluado_por=usuario, **datos)
    registrar_auditoria(usuario, "CREAR", evaluacion)
    if evaluacion.resultado == "VALIDADO":
        _set_estado(convenio, "VALIDADO_TECNICAMENTE", usuario)
    elif evaluacion.resultado == "OBSERVADO":
        _set_estado(convenio, "OBSERVADO_DIGEP", usuario)
    return evaluacion


@transaction.atomic
def registrar_opinion_conapres(*, convenio: Convention, datos: dict, usuario) -> ConapresOpinion:
    _exigir_especifico(convenio, "La opinión CONAPRES")
    opinion = ConapresOpinion.objects.create(convenio=convenio, **datos)
    registrar_auditoria(usuario, "CREAR", opinion)
    if opinion.resultado_opinion == "FAVORABLE":
        _set_estado(convenio, "CONAPRES_FAVORABLE", usuario)
    elif opinion.resultado_opinion == "OBSERVADO":
        _set_estado(convenio, "CONAPRES_OBSERVADO", usuario)
    else:
        _set_estado(convenio, "PENDIENTE_CONAPRES", usuario)
    return opinion


@transaction.atomic
def definir_campo_clinico(*, convenio: Convention, datos: dict, usuario) -> ClinicalField:
    _exigir_especifico(convenio, "La definición de campos clínicos")
    if convenio.max_campos_clinicos is not None and datos["cantidad_maxima"] > convenio.max_campos_clinicos:
        raise ValidationError(
            {"cantidad_maxima": "Excede el máximo de campos clínicos del convenio."}
        )
    campo = ClinicalField.objects.create(convenio=convenio, **datos)
    registrar_auditoria(usuario, "CREAR", campo)
    _set_estado(convenio, "CAMPOS_CLINICOS_DEFINIDOS", usuario)
    return campo


@transaction.atomic
def registrar_opinion_juridica(*, convenio: Convention, datos: dict, usuario) -> LegalOpinion:
    opinion = LegalOpinion.objects.create(convenio=convenio, **datos)
    registrar_auditoria(usuario, "CREAR", opinion)
    if opinion.resultado_opinion == "FAVORABLE":
        _set_estado(convenio, "OGAJ_FAVORABLE", usuario)
    elif opinion.resultado_opinion == "OBSERVADO":
        _set_estado(convenio, "OGAJ_OBSERVADO", usuario)
    else:
        _set_estado(convenio, "PENDIENTE_OGAJ", usuario)
    return opinion


@transaction.atomic
def registrar_firma(*, convenio: Convention, datos: dict, usuario) -> Signature:
    """RN-9: no se puede firmar con observaciones técnicas/normativas/jurídicas pendientes."""
    if _tiene_observaciones_pendientes(convenio):
        raise ValidationError("No se puede firmar: hay observaciones pendientes de subsanar.")
    firma = Signature.objects.create(convenio=convenio, **datos)
    registrar_auditoria(usuario, "CREAR", firma)
    if firma.firmante_tipo_contenido.model == "minsaorgan":
        _set_estado(convenio, "FIRMADO_MINSA", usuario)
    else:
        _set_estado(convenio, "FIRMADO_EXTERNOS", usuario)
    return firma


@transaction.atomic
def publicar_convenio(*, convenio: Convention, datos: dict, usuario) -> Publication:
    publicacion = Publication.objects.create(convenio=convenio, creado_por=usuario, **datos)
    registrar_auditoria(usuario, "CREAR", publicacion)
    _set_estado(convenio, "PUBLICADO", usuario)
    return publicacion


@transaction.atomic
def agregar_participante(*, convenio: Convention, datos: dict, usuario) -> ConventionParticipant:
    participante = ConventionParticipant.objects.create(convenio=convenio, **datos)
    registrar_auditoria(usuario, "CREAR", participante)
    return participante
