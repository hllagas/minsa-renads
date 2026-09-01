"""Services del módulo Convenios: casos de uso de escritura y reglas de negocio (RN).

Toda escritura corre en `transaction.atomic()`, registra auditoría en
`bitacora_auditoria` y, si cambia el estado del convenio, en
`historial_estado_convenio`. Ver `docs/db_schema_modulo_01_convenios.md` y §6 del módulo.
"""

import datetime

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.common.services import registrar_auditoria
from apps.convenios.models import (
    ClinicalFieldAllocation,
    ClinicalFieldRegistration,
    ConapresOpinion,
    Convention,
    ConventionParticipant,
    ConventionStatus,
    ConventionStatusHistory,
    Ipress,
    LegalOpinion,
    OrganRepresentative,
    OrganRepresentativeHistory,
    ProfessionalCareer,
    Publication,
    Signature,
    TechnicalEvaluation,
    UniversityCareer,
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


def _avanzar_estado(convenio: Convention, codigo: str, usuario) -> None:
    """Avanza el convenio a `codigo` solo si es una transición hacia adelante.

    Idempotente y sin regresión: no hace nada si el convenio ya está en ese estado
    o en uno posterior (por `orden`). Útil para estados que dispara una sub-entidad
    (p. ej. `CAMPOS_CLINICOS_DEFINIDOS` al registrar campos clínicos) sin retroceder
    un convenio ya vigente.
    """
    destino = _obtener_estado(codigo)
    if destino.aplica_a == "ESPECIFICO" and convenio.tipo_convenio.codigo != "ESPECIFICO":
        return
    orden_actual = convenio.estado_actual.orden if convenio.estado_actual_id else 0
    if orden_actual < destino.orden:
        _set_estado(convenio, codigo, usuario)


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


def _exigir_marco(convenio: Convention, actividad: str) -> None:
    if convenio.tipo_convenio.codigo != "MARCO":
        raise ValidationError(f"{actividad} solo aplica a Convenios Marco.")


def _validar_partes_por_tipo(*, tipo_codigo, marco, universidad, unidad_ejecutora, facultad):
    """Valida las partes (unidad ejecutora / facultad) según el tipo de convenio.

    - MARCO: no lleva `unidad_ejecutora` ni `facultad` (deben ser nulos).
    - ESPECIFICO: `unidad_ejecutora` y `facultad` obligatorias; la facultad debe
      pertenecer a la universidad del Convenio Marco (o, para DIRIS sin Marco, a la
      universidad propia del Específico).

    Reusable por `crear_convenio`, `actualizar_convenio` y `crear_adenda`.
    """
    if tipo_codigo == "MARCO":
        if unidad_ejecutora is not None or facultad is not None:
            raise ValidationError(
                {"unidad_ejecutora": "Un Convenio Marco no lleva unidad ejecutora ni facultad."}
            )
    elif tipo_codigo == "ESPECIFICO":
        if unidad_ejecutora is None:
            raise ValidationError({"unidad_ejecutora": "Requerida para un Convenio Específico."})
        if facultad is None:
            raise ValidationError({"facultad": "Requerida para un Convenio Específico."})
        # La facultad debe pertenecer a la universidad del Marco; para DIRIS sin Marco,
        # a la universidad propia del Específico.
        universidad_esperada_id = marco.universidad_id if marco is not None else (
            universidad.id if universidad is not None else None
        )
        if universidad_esperada_id is not None and facultad.universidad_id != universidad_esperada_id:
            raise ValidationError(
                {"facultad": "La facultad debe pertenecer a la universidad del Convenio Marco."}
            )


def _exigir_campos_clinicos_conapres(convenio: Convention) -> None:
    """Gate de suscripción: exige campos clínicos registrados por CONAPRES con resolución.

    Solo aplica a Convenios Específicos. Exige ≥1 `ClinicalFieldRegistration` del
    convenio sobre una sede docente (`ipress.es_sede_docente=True`) de la unidad
    ejecutora del convenio (`ipress.unidad_ejecutora_id == convenio.unidad_ejecutora_id`)
    con `numero_resolucion_conapres` no vacío.

    Se engancha en `registrar_firma` (primer punto de escritura de suscripción con
    service dedicado) y en `cambiar_estado` cuando el destino es `ENVIADO_SG`.
    """
    if convenio.tipo_convenio.codigo != "ESPECIFICO":
        return
    existe = (
        convenio.campos_clinicos.filter(
            ipress__es_sede_docente=True,
            ipress__unidad_ejecutora_id=convenio.unidad_ejecutora_id,
        )
        .exclude(numero_resolucion_conapres="")
        .exists()
    )
    if not existe:
        raise ValidationError(
            "No se puede avanzar a suscripción: falta al menos un campo clínico "
            "registrado por CONAPRES (con resolución) sobre una sede docente de la "
            "unidad ejecutora."
        )


# ---------------------------------------------------------------------------
# Casos de uso
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_convenio(*, datos: dict, usuario) -> Convention:
    """Registra un convenio. RN-3: el Específico requiere un Marco vigente."""
    tipo = datos["tipo_convenio"]
    marco = datos.get("convenio_marco")
    organo = datos["organo_directorio"]
    categoria = organo.categoria  # ORGANO_MINSA / UNIVERSIDAD / GOBIERNO_REGIONAL / MINSA_DIRIS / UNIDAD_EJECUTORA

    if tipo.codigo == "MARCO":
        # RN-1: solo un Gobierno Regional (GERESA/DIRESA) puede solicitar un Convenio Marco.
        if categoria != "GOBIERNO_REGIONAL":
            raise ValidationError(
                {"organo_directorio": "Solo una GERESA o DIRESA puede solicitar un Convenio Marco."}
            )
        if marco is not None:
            raise ValidationError({"convenio_marco": "Un Convenio Marco no depende de otro convenio."})
    elif tipo.codigo == "ESPECIFICO":
        # RN-3: requiere Convenio Marco vigente, salvo DIRIS (MINSA_DIRIS, no requiere Marco).
        if categoria == "MINSA_DIRIS":
            if marco is not None and (
                not marco.estado_actual_id or marco.estado_actual.codigo not in ESTADOS_VIGENTES
            ):
                raise ValidationError({"convenio_marco": "El Convenio Marco debe estar vigente."})
        else:
            if marco is None:
                raise ValidationError({"convenio_marco": "Requerido para un Convenio Específico."})
            if not marco.estado_actual_id or marco.estado_actual.codigo not in ESTADOS_VIGENTES:
                raise ValidationError({"convenio_marco": "El Convenio Marco debe estar vigente."})

    # Validación de partes por tipo (unidad ejecutora / facultad).
    _validar_partes_por_tipo(
        tipo_codigo=tipo.codigo,
        marco=marco,
        universidad=datos["universidad"],
        unidad_ejecutora=datos.get("unidad_ejecutora"),
        facultad=datos.get("facultad"),
    )

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
        organo_directorio=datos["organo_directorio"],
        universidad=datos["universidad"],
        unidad_ejecutora=datos.get("unidad_ejecutora"),
        facultad=datos.get("facultad"),
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
def crear_adenda(*, convenio_origen: Convention, datos: dict, usuario) -> Convention:
    """Crea una adenda de ampliación de un convenio (Marco o Específico), sin límite.

    La adenda es una fila `convenio` encadenada por `convenio_origen`, con nuevo
    periodo de vigencia. Hereda del origen tipo, marco, universidad, órgano del
    directorio, unidad ejecutora, facultad y solicitante polimórfico. No valida
    profundidad de la cadena (adendas de adendas permitidas).

    La adenda de un Marco hereda `unidad_ejecutora`/`facultad` como `None` (el Marco
    no las tiene); la de un Específico las hereda del origen.
    """
    tipo = convenio_origen.tipo_convenio

    fecha_inicio = datos.get("fecha_inicio")
    if not fecha_inicio:
        raise ValidationError({"fecha_inicio": "Requerida para crear una adenda."})
    fecha_fin = datos.get("fecha_fin")
    if not fecha_fin and tipo.anios_vigencia:
        fecha_fin = _sumar_anios(fecha_inicio, tipo.anios_vigencia)
    if fecha_fin and fecha_fin <= fecha_inicio:
        raise ValidationError({"fecha_fin": "Debe ser posterior a la fecha de inicio."})

    titulo = datos.get("titulo") or f"{convenio_origen.titulo} (Adenda)"

    estado_inicial = _obtener_estado("SOLICITUD_REGISTRADA")
    adenda = Convention.objects.create(
        tipo_convenio=tipo,
        convenio_marco=convenio_origen.convenio_marco,
        convenio_origen=convenio_origen,
        es_adenda=True,
        plantilla=convenio_origen.plantilla,
        codigo=datos.get("codigo", ""),
        titulo=titulo,
        solicitante_tipo_contenido_id=convenio_origen.solicitante_tipo_contenido_id,
        solicitante_id_objeto=convenio_origen.solicitante_id_objeto,
        organo_directorio=convenio_origen.organo_directorio,
        universidad=convenio_origen.universidad,
        unidad_ejecutora=convenio_origen.unidad_ejecutora,
        facultad=convenio_origen.facultad,
        estado_actual=estado_inicial,
        fecha_solicitud=datos.get("fecha_solicitud") or datetime.date.today(),
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        max_campos_clinicos=convenio_origen.max_campos_clinicos,
        creado_por=usuario,
    )
    ConventionStatusHistory.objects.create(
        convenio=adenda, estado=estado_inicial, cambiado_por=usuario
    )
    registrar_auditoria(usuario, "CREAR", adenda)
    return adenda


@transaction.atomic
def actualizar_convenio(*, convenio: Convention, datos: dict, usuario) -> Convention:
    """Actualiza campos editables del convenio (no el estado: usar `cambiar_estado`)."""
    editables = [
        "codigo", "titulo", "plantilla", "organo_directorio", "universidad",
        "unidad_ejecutora", "facultad",
        "fecha_inicio", "fecha_fin", "max_campos_clinicos",
    ]
    for campo in editables:
        if campo in datos:
            setattr(convenio, campo, datos[campo])
    # Revalidar partes por tipo contra el estado final del objeto (no solo el
    # payload) para no permitir estados incoherentes vía PATCH parcial.
    _validar_partes_por_tipo(
        tipo_codigo=convenio.tipo_convenio.codigo,
        marco=convenio.convenio_marco,
        universidad=convenio.universidad,
        unidad_ejecutora=convenio.unidad_ejecutora,
        facultad=convenio.facultad,
    )
    convenio.save()
    registrar_auditoria(usuario, "ACTUALIZAR", convenio)
    return convenio


@transaction.atomic
def cambiar_estado(*, convenio: Convention, nuevo_estado_codigo: str, usuario, observacion: str = "") -> Convention:
    # Gate de suscripción: avanzar un Específico a ENVIADO_SG exige campos clínicos
    # con resolución CONAPRES sobre sede docente de la unidad ejecutora (TODO D1).
    if nuevo_estado_codigo == "ENVIADO_SG":
        _exigir_campos_clinicos_conapres(convenio)
    convenio = _set_estado(convenio, nuevo_estado_codigo, usuario, observacion)
    # Efecto de vigencia: al pasar una adenda a VIGENTE, marcar el origen como AMPLIADO
    # (con guarda: no reactivar un origen ya CERRADO/ANULADO/AMPLIADO).
    if (
        nuevo_estado_codigo == "VIGENTE"
        and convenio.es_adenda
        and convenio.convenio_origen_id
    ):
        origen = convenio.convenio_origen
        estado_origen = origen.estado_actual.codigo if origen.estado_actual_id else ""
        if estado_origen not in {"CERRADO", "ANULADO", "AMPLIADO"}:
            _set_estado(
                origen, "AMPLIADO", usuario,
                observacion=f"Ampliado por adenda #{convenio.id}",
            )
    return convenio


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


# ---------------------------------------------------------------------------
# Campos clínicos — Registro (CONAPRES) y Asignación (Órgano Regional)
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_registro_campo_clinico(*, datos: dict, usuario) -> ClinicalFieldRegistration:
    """Registra (CONAPRES) el total de campos clínicos por sede docente + carrera.

    RN — sede docente: la IPRESS debe estar autorizada (`es_sede_docente=True`).
    Opcional: si el convenio fija `max_campos_clinicos`, el total no puede excederlo.
    """
    ipress = datos["ipress"]
    if not ipress.es_sede_docente:
        raise ValidationError(
            {"ipress": "La IPRESS debe estar autorizada como sede docente por CONAPRES."}
        )
    convenio = datos["convenio"]
    # RN — la sede docente debe pertenecer a la unidad ejecutora del Convenio Específico.
    # Se valida solo cuando el convenio ya tiene unidad ejecutora (los convenios previos
    # a esta mejora podrían no tenerla y quedan exentos del chequeo).
    if (
        convenio.unidad_ejecutora_id is not None
        and ipress.unidad_ejecutora_id != convenio.unidad_ejecutora_id
    ):
        raise ValidationError(
            {"ipress": "La sede docente debe pertenecer a la unidad ejecutora del Convenio Específico."}
        )
    if (
        convenio.max_campos_clinicos is not None
        and datos["campos_clinicos_registrados"] > convenio.max_campos_clinicos
    ):
        raise ValidationError(
            {"campos_clinicos_registrados": "Excede el máximo de campos clínicos del convenio."}
        )
    registro = ClinicalFieldRegistration.objects.create(
        campos_clinicos_asignados=0, creado_por=usuario, **datos
    )
    registrar_auditoria(usuario, "CREAR", registro)
    # RN — flujo del convenio: registrar campos clínicos (CONAPRES) avanza el
    # Convenio Específico a CAMPOS_CLINICOS_DEFINIDOS (forward-only, idempotente).
    _avanzar_estado(convenio, "CAMPOS_CLINICOS_DEFINIDOS", usuario)
    return registro


@transaction.atomic
def actualizar_registro_campo_clinico(
    *, registro: ClinicalFieldRegistration, datos: dict, usuario
) -> ClinicalFieldRegistration:
    """Actualiza (CONAPRES) un registro de campos clínicos.

    No permite editar `campos_clinicos_asignados` (lo maneja el acumulador) y el
    total registrado no puede quedar por debajo de lo ya asignado a universidades.
    """
    editables = [
        "convenio", "ipress", "carrera_profesional", "especialidad",
        "campos_clinicos_registrados",
        "numero_resolucion_conapres", "fecha_resolucion_conapres",
    ]
    for campo in editables:
        if campo in datos:
            setattr(registro, campo, datos[campo])

    if not registro.ipress.es_sede_docente:
        raise ValidationError(
            {"ipress": "La IPRESS debe estar autorizada como sede docente por CONAPRES."}
        )
    if registro.campos_clinicos_registrados < registro.campos_clinicos_asignados:
        raise ValidationError(
            {"campos_clinicos_registrados": "No puede ser menor que los campos ya asignados a universidades."}
        )
    registro.actualizado_por = usuario
    registro.save()
    registrar_auditoria(usuario, "ACTUALIZAR", registro)
    return registro


def _recalcular_asignados(registro: ClinicalFieldRegistration) -> None:
    """Fuente única del acumulador `campos_clinicos_asignados` del registro.

    Recalcula la suma de `campos_clinicos_autorizados` de todas las asignaciones
    del registro y la persiste. Debe invocarse dentro de la misma transacción de
    create/update/delete de asignaciones.
    """
    total = registro.asignaciones.aggregate(total=Sum("campos_clinicos_autorizados"))["total"] or 0
    registro.campos_clinicos_asignados = total
    registro.save(update_fields=["campos_clinicos_asignados", "actualizado_en"])


def _validar_convenio_asignacion(convenio: Convention) -> None:
    """Valida que el convenio de la asignación sea Específico y esté vigente (b)."""
    _exigir_especifico(convenio, "La asignación de campos clínicos")
    if not convenio.estado_actual_id or convenio.estado_actual.codigo not in ESTADOS_VIGENTES:
        raise ValidationError({"convenio": "El Convenio Específico debe estar vigente."})


def _disponibilidad_registro(registro: ClinicalFieldRegistration, excluir_pk=None) -> int:
    """Cupos disponibles = registrados − Σ autorizados de las OTRAS asignaciones."""
    qs = registro.asignaciones.all()
    if excluir_pk is not None:
        qs = qs.exclude(pk=excluir_pk)
    usados = qs.aggregate(total=Sum("campos_clinicos_autorizados"))["total"] or 0
    return registro.campos_clinicos_registrados - usados


@transaction.atomic
def crear_asignacion_campo_clinico(*, datos: dict, usuario) -> ClinicalFieldAllocation:
    """Asigna (Órgano Regional) campos clínicos a una universidad contra un registro.

    RN — disponibilidad: `campos_clinicos_autorizados` no puede exceder los cupos
    disponibles del registro padre. RN — convenio Específico vigente. La sede
    (`ipress`), carrera, especialidad y `universidad` se **derivan** del registro
    padre y del convenio (el cliente no las envía).
    """
    registro = ClinicalFieldRegistration.objects.select_for_update().get(
        pk=datos["campo_clinico_ipress"].pk
    )
    convenio = datos["convenio"]
    _validar_convenio_asignacion(convenio)

    disponible = _disponibilidad_registro(registro)
    if datos["campos_clinicos_autorizados"] > disponible:
        raise ValidationError(
            {"campos_clinicos_autorizados": "Excede los campos clínicos disponibles del registro."}
        )

    asignacion = ClinicalFieldAllocation.objects.create(
        creado_por=usuario,
        ipress=registro.ipress,
        carrera_profesional=registro.carrera_profesional,
        especialidad=registro.especialidad,
        universidad=convenio.universidad,
        **datos,
    )
    _recalcular_asignados(registro)
    registrar_auditoria(usuario, "CREAR", asignacion)
    return asignacion


@transaction.atomic
def actualizar_asignacion_campo_clinico(
    *, asignacion: ClinicalFieldAllocation, datos: dict, usuario
) -> ClinicalFieldAllocation:
    """Actualiza (Órgano Regional) una asignación, revalidando la disponibilidad."""
    registro = ClinicalFieldRegistration.objects.select_for_update().get(
        pk=asignacion.campo_clinico_ipress_id
    )
    editables = ["campos_clinicos_autorizados", "fecha_inicio", "fecha_fin"]
    for campo in editables:
        if campo in datos:
            setattr(asignacion, campo, datos[campo])

    disponible = _disponibilidad_registro(registro, excluir_pk=asignacion.pk)
    if asignacion.campos_clinicos_autorizados > disponible:
        raise ValidationError(
            {"campos_clinicos_autorizados": "Excede los campos clínicos disponibles del registro."}
        )
    asignacion.actualizado_por = usuario
    asignacion.save()
    _recalcular_asignados(registro)
    registrar_auditoria(usuario, "ACTUALIZAR", asignacion)
    return asignacion


@transaction.atomic
def eliminar_asignacion_campo_clinico(*, asignacion: ClinicalFieldAllocation, usuario) -> None:
    """Elimina (Órgano Regional) una asignación y recalcula el acumulador del registro.

    Si hay internados que la referencian, el `PROTECT` de `Internship` impide el
    borrado (la vista lo traduce a 409).
    """
    registro = ClinicalFieldRegistration.objects.select_for_update().get(
        pk=asignacion.campo_clinico_ipress_id
    )
    pk = asignacion.pk
    asignacion.delete()
    asignacion.pk = pk
    _recalcular_asignados(registro)
    registrar_auditoria(usuario, "ELIMINAR", asignacion)


@transaction.atomic
def registrar_opinion_juridica(*, convenio: Convention, datos: dict, usuario) -> LegalOpinion:
    _exigir_marco(convenio, "La opinión jurídica de OGAJ")
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
    # Gate de suscripción (solo Específicos): exige campos clínicos con resolución
    # CONAPRES sobre sede docente de la unidad ejecutora (TODO D1 — validator confirma).
    _exigir_campos_clinicos_conapres(convenio)
    if _tiene_observaciones_pendientes(convenio):
        raise ValidationError("No se puede firmar: hay observaciones pendientes de subsanar.")
    firma = Signature.objects.create(convenio=convenio, **datos)
    registrar_auditoria(usuario, "CREAR", firma)
    if firma.firmante_tipo_contenido.model == "organdirectory":
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


# ---------------------------------------------------------------------------
# Representantes de órgano (directorio) — histórico de bajas
# ---------------------------------------------------------------------------
_CAMPOS_SNAPSHOT_REPRESENTANTE = [
    "organo_directorio", "nombre", "tipo_documento_identidad",
    "numero_documento_identidad", "sexo", "cargo_ejecutivo",
    "fecha_inicio_designacion", "numero_resolucion_designacion",
    "fecha_inicio_facultades",
]


@transaction.atomic
def registrar_organo_representante(*, datos: dict, usuario) -> OrganRepresentative:
    """Registra un representante de órgano, dando de baja al anterior activo del mismo par.

    RN — histórico de representantes: al designar un nuevo representante para un par
    ``(organo_directorio, cargo_ejecutivo)`` que ya tiene uno activo, el anterior se
    marca ``activo=False`` y se copia a ``OrganRepresentativeHistory`` (snapshot
    denormalizado) con ``fecha_baja=hoy``. Todo en una transacción, con auditoría.
    """
    motivo = datos.pop("motivo", "") or "Reemplazo de representante"

    anterior = (
        OrganRepresentative.objects.select_for_update()
        .filter(
            organo_directorio=datos["organo_directorio"],
            cargo_ejecutivo=datos["cargo_ejecutivo"],
            activo=True,
        )
        .first()
    )
    if anterior is not None:
        anterior.activo = False
        anterior.save(update_fields=["activo"])
        historial = OrganRepresentativeHistory.objects.create(
            representante=anterior,
            fecha_baja=datetime.date.today(),
            motivo=motivo,
            **{campo: getattr(anterior, campo) for campo in _CAMPOS_SNAPSHOT_REPRESENTANTE},
        )
        registrar_auditoria(
            usuario, "CAMBIO_ESTADO", anterior,
            nombre_campo="activo", valor_anterior="True", valor_nuevo="False",
        )
        registrar_auditoria(usuario, "CREAR", historial)

    nuevo = OrganRepresentative.objects.create(**datos)
    registrar_auditoria(usuario, "CREAR", nuevo)
    return nuevo


@transaction.atomic
def autorizar_sede_docente(*, ipress: Ipress, usuario, autorizar: bool = True) -> Ipress:
    """CONAPRES autoriza/registra una IPRESS como sede docente.

    CONAPRES verifica los criterios (establecimiento asistencial, del MINSA o de la
    sanidad de las FF.AA./FF.PP., de gestión pública) antes de autorizar. Aquí se
    registra la decisión; solo una sede autorizada puede recibir campos clínicos.
    """
    anterior = ipress.es_sede_docente
    ipress.es_sede_docente = autorizar
    ipress.save(update_fields=["es_sede_docente"])
    registrar_auditoria(
        usuario, "ACTUALIZAR", ipress,
        nombre_campo="es_sede_docente", valor_anterior=anterior, valor_nuevo=autorizar,
    )
    return ipress


# ---------------------------------------------------------------------------
# Carreras por facultad (sincronización en lote)
# ---------------------------------------------------------------------------
@transaction.atomic
def sincronizar_carreras_facultad(*, facultad, carreras_ids, usuario) -> list[UniversityCareer]:
    """Sincroniza (idempotente) las carreras de una facultad en `universidad_carrera`.

    La `universidad` se deriva de `facultad.universidad` (no se recibe del cliente).
    Por cada carrera enviada se hace un upsert de la fila `(universidad, carrera)`
    respetando `unique_together` (RN-FC-01): si ya existe se reactiva y se le fija
    esta facultad; si no, se crea. Las filas **de esta facultad** cuya carrera ya no
    esté en `carreras_ids` se dan de baja (`activo=False`, sin borrado físico). El
    alcance de baja es por facultad: no afecta carreras registradas contra otra
    facultad de la misma universidad. Toda alta/reactivación/baja real queda auditada.

    Devuelve las filas activas resultantes de la facultad.
    """
    universidad = facultad.universidad

    # Normaliza a un conjunto de enteros y valida existencia (RN-FC-01).
    ids_solicitados: set[int] = set()
    for carrera in carreras_ids:
        carrera_id = carrera.id if isinstance(carrera, ProfessionalCareer) else int(carrera)
        ids_solicitados.add(carrera_id)

    existentes = set(
        ProfessionalCareer.objects.filter(id__in=ids_solicitados).values_list("id", flat=True)
    )
    faltantes = ids_solicitados - existentes
    if faltantes:
        raise ValidationError(
            f"Carrera(s) profesional(es) inexistente(s): {sorted(faltantes)}."
        )

    # RN-FC-02 (defensiva): la facultad debe pertenecer a la universidad derivada.
    if facultad.universidad_id != universidad.id:
        raise ValidationError("La facultad no pertenece a la universidad indicada.")

    # Alta / reactivación de las carreras enviadas (RN-FC-04: una carrera activa
    # de la universidad pertenece a UNA sola facultad y no puede ser tomada por
    # otra facultad mientras siga activa).
    for carrera_id in ids_solicitados:
        fila = UniversityCareer.objects.filter(
            universidad=universidad, carrera_profesional_id=carrera_id
        ).first()
        if fila is None:
            fila = UniversityCareer.objects.create(
                universidad=universidad,
                carrera_profesional_id=carrera_id,
                facultad=facultad,
                activo=True,
            )
            registrar_auditoria(usuario, "CREAR", fila)
        elif fila.facultad_id == facultad.id:
            # Misma facultad: solo reactivar si estaba dada de baja.
            if not fila.activo:
                fila.activo = True
                fila.save(update_fields=["activo"])
                registrar_auditoria(usuario, "ACTUALIZAR", fila)
        elif fila.activo:
            # Ya asignada y activa en otra facultad de la misma universidad → bloquear.
            raise ValidationError(
                f"La carrera profesional {carrera_id} ya está asignada a otra "
                "facultad de esta universidad; no puede asignarse a esta facultad."
            )
        else:
            # Estaba libre (dada de baja en otra facultad): esta facultad la toma.
            fila.facultad = facultad
            fila.activo = True
            fila.save(update_fields=["facultad", "activo"])
            registrar_auditoria(usuario, "ACTUALIZAR", fila)

    # Baja (por facultad) de las carreras que ya no están en la lista enviada.
    a_dar_de_baja = UniversityCareer.objects.filter(
        facultad=facultad, activo=True
    ).exclude(carrera_profesional_id__in=ids_solicitados)
    for fila in a_dar_de_baja:
        fila.activo = False
        fila.save(update_fields=["activo"])
        registrar_auditoria(
            usuario, "ACTUALIZAR", fila,
            nombre_campo="activo", valor_anterior=True, valor_nuevo=False,
        )

    return list(
        UniversityCareer.objects.filter(facultad=facultad, activo=True).order_by("id")
    )
