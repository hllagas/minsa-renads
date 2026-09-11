"""Services del módulo Convenios: casos de uso de escritura y reglas de negocio (RN).

Toda escritura corre en `transaction.atomic()`, registra auditoría en
`bitacora_auditoria` y, si cambia el estado del convenio, en
`historial_estado_convenio`. Ver `docs/db_schema_modulo_01_convenios.md` y §6 del módulo.
"""

import datetime

import openpyxl
from django.contrib.contenttypes.models import ContentType
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
    ConventionParty,
    ConventionStatus,
    ConventionStatusHistory,
    ConventionType,
    ExecutingUnit,
    Faculty,
    Ipress,
    LegalOpinion,
    OrganDirectory,
    OrganRepresentative,
    OrganRepresentativeHistory,
    ProfessionalCareer,
    Publication,
    RegionalGovernment,
    Signature,
    TechnicalEvaluation,
    UniversityCareer,
    University,
    Specialty,
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


def _validar_nomenclatura(convenio: Convention, nomenclatura: str) -> None:
    """Gate de nomenclatura del Convenio Marco (se asigna al aprobar DIGEP)."""
    if convenio.tipo_convenio.codigo != "MARCO":
        raise ValidationError({"nomenclatura": "La nomenclatura solo aplica a Convenios Marco."})
    if not (nomenclatura or "").strip():
        raise ValidationError(
            {"nomenclatura": "Requerida para aprobar la validación técnica del Marco."}
        )


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


def _validar_gobierno_regional_por_tipo(*, tipo_codigo, categoria_organo, gobierno_regional) -> None:
    """Valida el `gobierno_regional` del convenio según su tipo/categoría (RN-GORE-1/2).

    - MARCO + órgano GOBIERNO_REGIONAL (región): exige `gobierno_regional` no nulo.
    - MARCO + cualquier otro órgano: `gobierno_regional` debe ser nulo.
    - ESPECIFICO: `gobierno_regional` debe ser nulo (se deriva del Marco).

    Reutilizado por `crear_convenio` y `actualizar_convenio`, coherente con
    `_validar_partes_por_tipo`.
    """
    if tipo_codigo == "MARCO":
        if categoria_organo == "GOBIERNO_REGIONAL":
            if gobierno_regional is None:
                raise ValidationError(
                    {"gobierno_regional": "Requerido para un Convenio Marco regional."}
                )
        elif gobierno_regional is not None:
            raise ValidationError(
                {"gobierno_regional": "Solo un Convenio Marco regional lleva gobierno regional."}
            )
    elif tipo_codigo == "ESPECIFICO":
        if gobierno_regional is not None:
            raise ValidationError(
                {"gobierno_regional": "Un Convenio Específico no lleva gobierno regional."}
            )


def _validar_composicion_partes(*, tipo_codigo, categoria_organo, roles_presentes) -> None:
    """Valida la composición de roles requerida por tipo/categoría del convenio.

    - MARCO + órgano GOBIERNO_REGIONAL (región): requiere MINSA + GOBIERNO_REGIONAL + UNIVERSIDAD.
    - MARCO + cualquier otro órgano (ORGANO_MINSA, UNIVERSIDAD, MINSA_DIRIS): requiere MINSA + UNIVERSIDAD.
    - ESPECIFICO: requiere UNIDAD_EJECUTORA + FACULTAD (apoderado orden=2 opcional).

    `roles_presentes` es un conjunto/colección de códigos de rol (PARTY_ROLE).
    """
    roles = set(roles_presentes)
    if tipo_codigo == "MARCO":
        if categoria_organo == "GOBIERNO_REGIONAL":
            requeridos = {"MINSA", "GOBIERNO_REGIONAL", "UNIVERSIDAD"}
        else:
            requeridos = {"MINSA", "UNIVERSIDAD"}
    elif tipo_codigo == "ESPECIFICO":
        requeridos = {"UNIDAD_EJECUTORA", "FACULTAD"}
    else:
        requeridos = set()

    faltantes = requeridos - roles
    if faltantes:
        etiquetas = ", ".join(sorted(faltantes))
        raise ValidationError(
            f"Faltan las partes requeridas para este tipo de convenio: {etiquetas}."
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
        ClinicalFieldRegistration.objects.filter(
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
        # RN-1: Gobierno Regional, Ministerio de Salud o Universidad pueden solicitar un Marco.
        _CATEGORIAS_MARCO = {"GOBIERNO_REGIONAL", "ORGANO_MINSA", "UNIVERSIDAD"}
        if categoria not in _CATEGORIAS_MARCO:
            raise ValidationError(
                {"organo_directorio": "Un Convenio Marco solo puede ser solicitado por un Gobierno Regional, el Ministerio de Salud o una Universidad."}
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
    # Validación del gobierno regional por tipo (RN-GORE-1/2).
    _validar_gobierno_regional_por_tipo(
        tipo_codigo=tipo.codigo,
        categoria_organo=categoria,
        gobierno_regional=datos.get("gobierno_regional"),
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
        nomenclatura=datos.get("nomenclatura", ""),
        titulo=datos["titulo"],
        solicitante_tipo_contenido=datos["solicitante_tipo_contenido"],
        solicitante_id_objeto=datos["solicitante_id_objeto"],
        organo_directorio=datos["organo_directorio"],
        gobierno_regional=datos.get("gobierno_regional"),
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
    directorio, gobierno regional, unidad ejecutora, facultad y solicitante
    polimórfico. No valida profundidad de la cadena (adendas de adendas permitidas).

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
        nomenclatura=datos.get("nomenclatura", ""),
        titulo=titulo,
        solicitante_tipo_contenido_id=convenio_origen.solicitante_tipo_contenido_id,
        solicitante_id_objeto=convenio_origen.solicitante_id_objeto,
        organo_directorio=convenio_origen.organo_directorio,
        gobierno_regional=convenio_origen.gobierno_regional,
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
    # `nomenclatura` habilitado temporalmente para edición directa (Específicos).
    editables = [
        "titulo", "nomenclatura", "plantilla", "organo_directorio", "gobierno_regional",
        "universidad", "unidad_ejecutora", "facultad",
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
    # Revalidar el gobierno regional por tipo contra el estado final (RN-GORE-1/2).
    _validar_gobierno_regional_por_tipo(
        tipo_codigo=convenio.tipo_convenio.codigo,
        categoria_organo=convenio.organo_directorio.categoria,
        gobierno_regional=convenio.gobierno_regional,
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
    # `nomenclatura` no es campo de `evaluacion_tecnica`: se recibe por el serializer
    # de la acción y se persiste en el convenio (solo Marco validado).
    nomenclatura = datos.pop("nomenclatura", None)
    evaluacion = TechnicalEvaluation.objects.create(convenio=convenio, evaluado_por=usuario, **datos)
    registrar_auditoria(usuario, "CREAR", evaluacion)
    if evaluacion.resultado == "VALIDADO":
        # Gate de nomenclatura: al aprobar DIGEP un Convenio Marco, exige y persiste
        # la nomenclatura oficial ANTES de pasar a VALIDADO_TECNICAMENTE.
        if convenio.tipo_convenio.codigo == "MARCO":
            _validar_nomenclatura(convenio, nomenclatura or "")
            anterior = convenio.nomenclatura
            convenio.nomenclatura = nomenclatura.strip()
            convenio.save(update_fields=["nomenclatura", "actualizado_en"])
            registrar_auditoria(
                usuario, "ACTUALIZAR", convenio,
                nombre_campo="nomenclatura", valor_anterior=anterior, valor_nuevo=convenio.nomenclatura,
            )
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
    registro = ClinicalFieldRegistration.objects.create(
        campos_clinicos_asignados=0, creado_por=usuario, **datos
    )
    registrar_auditoria(usuario, "CREAR", registro)
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
        "ipress", "carrera_profesional", "especialidad",
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
    fecha_inicio = datos.pop("fecha_inicio", None)
    fecha_fin = datos.pop("fecha_fin", None)
    update_fields = []
    if fecha_inicio is not None:
        convenio.fecha_inicio = fecha_inicio
        update_fields.append("fecha_inicio")
    if fecha_fin is not None:
        convenio.fecha_fin = fecha_fin
        update_fields.append("fecha_fin")
    if update_fields:
        convenio.save(update_fields=update_fields)
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
    "tipo_contenido", "id_objeto", "nombre", "tipo_documento_identidad",
    "numero_documento_identidad", "sexo", "cargo_ejecutivo",
    "fecha_inicio_designacion", "numero_resolucion_designacion",
    "numero_resolucion_facultades",
    "fecha_inicio_facultades",
]


@transaction.atomic
def registrar_organo_representante(*, datos: dict, usuario) -> OrganRepresentative:
    """Registra un representante de entidad, dando de baja al anterior activo del mismo par.

    RN — histórico de representantes: al designar un nuevo representante para un par
    ``(tipo_contenido, id_objeto, cargo_ejecutivo)`` (entidad × cargo) que ya tiene uno
    activo, el anterior se marca ``activo=False`` y se copia a
    ``OrganRepresentativeHistory`` (snapshot denormalizado) con ``fecha_baja=hoy``.
    Todo en una transacción, con auditoría. Entidades distintas con el mismo cargo no
    se afectan entre sí.
    """
    motivo = datos.pop("motivo", "") or "Reemplazo de representante"

    anterior = (
        OrganRepresentative.objects.select_for_update()
        .filter(
            tipo_contenido=datos["tipo_contenido"],
            id_objeto=datos["id_objeto"],
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


# ---------------------------------------------------------------------------
# Partes firmantes del convenio (sincronización en lote)
# ---------------------------------------------------------------------------
def _validar_coherencia_parte(*, organo_directorio, organo_representante, cargo_ejecutivo) -> None:
    """Coherencia órgano↔representante↔cargo de una parte firmante.

    - El representante (si se envía) debe representar al mismo órgano del directorio.
      Tras el modelo polimórfico, esto es: su `entidad` es ese OrganDirectory
      (``tipo_contenido == organdirectory`` y ``id_objeto == organo_directorio.id``).
    - El cargo (si se envía y tiene órgano directivo) debe pertenecer al mismo órgano.
      Los cargos legacy sin ``organo_directivo`` no se validan.
    """
    if organo_representante is not None:
        representa_al_organo = (
            organo_representante.tipo_contenido.model == "organdirectory"
            and organo_representante.id_objeto == organo_directorio.id
        )
        if not representa_al_organo:
            raise ValidationError(
                {"organo_representante": "El representante no pertenece al órgano del directorio indicado."}
            )
    if (
        cargo_ejecutivo is not None
        and cargo_ejecutivo.organo_directivo_id
        and cargo_ejecutivo.organo_directivo_id != organo_directorio.id
    ):
        raise ValidationError(
            {"cargo_ejecutivo": "El cargo no pertenece al órgano del directorio indicado."}
        )


@transaction.atomic
def sincronizar_partes(*, convenio: Convention, datos: list[dict], usuario) -> list[ConventionParty]:
    """Sincroniza (idempotente) las partes firmantes de un convenio.

    Cada elemento de ``datos`` es un dict con ``rol``, ``organo_directorio``,
    ``organo_representante`` (opcional), ``cargo_ejecutivo`` (opcional), ``orden`` y
    ``es_firmante``. Reconcilia por la clave ``(convenio, rol, orden)``: crea las
    partes nuevas, actualiza las existentes y elimina las que ya no estén en el
    payload. Valida la coherencia órgano↔representante↔cargo de cada parte y la
    composición de roles requerida según el tipo/categoría del convenio. Toda
    escritura queda auditada. Devuelve las partes resultantes del convenio.
    """
    # Normaliza el payload y valida coherencia por parte.
    entradas: dict[tuple[str, int], dict] = {}
    roles_presentes: set[str] = set()
    for item in datos:
        organo_directorio = item["organo_directorio"]
        organo_representante = item.get("organo_representante")
        cargo_ejecutivo = item.get("cargo_ejecutivo")
        _validar_coherencia_parte(
            organo_directorio=organo_directorio,
            organo_representante=organo_representante,
            cargo_ejecutivo=cargo_ejecutivo,
        )
        orden = item.get("orden", 1)
        clave = (item["rol"], orden)
        if clave in entradas:
            raise ValidationError(
                f"Parte duplicada para el rol {item['rol']} con orden {orden}."
            )
        entradas[clave] = {
            "rol": item["rol"],
            "organo_directorio": organo_directorio,
            "organo_representante": organo_representante,
            "cargo_ejecutivo": cargo_ejecutivo,
            "orden": orden,
            "es_firmante": item.get("es_firmante", True),
        }
        roles_presentes.add(item["rol"])

    # Composición de roles requerida por tipo/categoría (exigida al sincronizar).
    _validar_composicion_partes(
        tipo_codigo=convenio.tipo_convenio.codigo,
        categoria_organo=convenio.organo_directorio.categoria if convenio.organo_directorio_id else None,
        roles_presentes=roles_presentes,
    )

    existentes = {
        (parte.rol, parte.orden): parte
        for parte in convenio.partes_firmantes.select_for_update()
    }

    # Alta / actualización de las partes enviadas.
    for clave, valores in entradas.items():
        parte = existentes.get(clave)
        if parte is None:
            parte = ConventionParty.objects.create(convenio=convenio, **valores)
            registrar_auditoria(usuario, "CREAR", parte)
        else:
            cambiado = False
            for campo in ("organo_directorio", "organo_representante", "cargo_ejecutivo", "es_firmante"):
                if getattr(parte, campo) != valores[campo]:
                    setattr(parte, campo, valores[campo])
                    cambiado = True
            if cambiado:
                parte.save(update_fields=[
                    "organo_directorio", "organo_representante", "cargo_ejecutivo", "es_firmante",
                ])
                registrar_auditoria(usuario, "ACTUALIZAR", parte)

    # Baja (delete) de las partes que ya no están en el payload.
    for clave, parte in existentes.items():
        if clave not in entradas:
            pk = parte.pk
            parte.delete()
            parte.pk = pk
            registrar_auditoria(usuario, "ELIMINAR", parte)

    return list(convenio.partes_firmantes.order_by("orden", "id"))


# ---------------------------------------------------------------------------
# Carga masiva de convenios (solo Administrador RENADS)
# ---------------------------------------------------------------------------
# Columnas requeridas mínimas del Excel.
BULK_CONV_COLUMNAS_REQUERIDAS = {
    "tipo_convenio", "titulo", "organo_directorio", "universidad", "fecha_solicitud",
}

# Alias de encabezados con sufijo `_id` → clave canónica interna.
BULK_CONV_ALIAS_COLUMNAS = {
    "organo_directorio_id": "organo_directorio",
    "convenio_marco_id": "convenio_marco",
    "gobierno_regional_id": "gobierno_regional",
    "universidad_id": "universidad",
    "unidad_ejecutora_id": "unidad_ejecutora",
    "facultad_id": "facultad",
}

# Estados destino permitidos en carga masiva.
_ESTADOS_BULK_PERMITIDOS = {"VIGENTE", "PUBLICADO"}


def _bc_celda(valor):
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def _bc_fecha(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    try:
        return datetime.date.fromisoformat(str(valor).strip()[:10])
    except ValueError as exc:
        raise ValidationError("Fecha inválida (use YYYY-MM-DD).") from exc


def _bc_resolver_tipo(valor) -> ConventionType:
    if not valor:
        raise ValidationError("`tipo_convenio` es requerido.")
    texto = str(valor).strip().upper()
    try:
        return ConventionType.objects.get(codigo=texto)
    except ConventionType.DoesNotExist as exc:
        raise ValidationError(f"Tipo de convenio no encontrado: {valor}. Valores: MARCO, ESPECIFICO.") from exc


def _bc_resolver_organo(valor) -> OrganDirectory:
    if valor is None:
        raise ValidationError("`organo_directorio` es requerido.")
    texto = str(valor).strip()
    try:
        return OrganDirectory.objects.get(id=int(texto)) if texto.isdigit() else OrganDirectory.objects.get(nombre__iexact=texto)
    except OrganDirectory.DoesNotExist as exc:
        raise ValidationError(f"Órgano directorio no encontrado: {valor}.") from exc
    except OrganDirectory.MultipleObjectsReturned as exc:
        raise ValidationError(f"Órgano directorio ambiguo (use el id): {valor}.") from exc


def _bc_resolver_universidad(valor) -> University:
    if valor is None:
        raise ValidationError("`universidad` es requerida.")
    texto = str(valor).strip()
    try:
        if texto.isdigit():
            return University.objects.get(id=int(texto))
        return University.objects.get(codigo_inei=texto)
    except University.DoesNotExist as exc:
        raise ValidationError(f"Universidad no encontrada: {valor}.") from exc


def _bc_resolver_convenio_marco(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto.isdigit():
        raise ValidationError("`convenio_marco` debe ser el ID numérico del Convenio Marco.")
    try:
        return Convention.objects.get(id=int(texto))
    except Convention.DoesNotExist as exc:
        raise ValidationError(f"Convenio Marco no encontrado: id={texto}.") from exc


def _bc_resolver_gobierno_regional(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    try:
        return RegionalGovernment.objects.get(id=int(texto)) if texto.isdigit() else RegionalGovernment.objects.get(nombre__iexact=texto)
    except RegionalGovernment.DoesNotExist as exc:
        raise ValidationError(f"Gobierno Regional no encontrado: {valor}.") from exc


def _bc_resolver_unidad_ejecutora(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    try:
        if texto.isdigit():
            return ExecutingUnit.objects.get(id=int(texto))
        return ExecutingUnit.objects.get(codigo=texto)
    except ExecutingUnit.DoesNotExist as exc:
        raise ValidationError(f"Unidad ejecutora no encontrada: {valor}.") from exc


def _bc_resolver_facultad(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto.isdigit():
        raise ValidationError("`facultad` debe ser el ID numérico de la facultad.")
    try:
        return Faculty.objects.get(id=int(texto))
    except Faculty.DoesNotExist as exc:
        raise ValidationError(f"Facultad no encontrada: id={texto}.") from exc


def _bc_validar_fila(tipo, organo, marco, gobierno_regional, unidad_ejecutora, facultad, universidad):
    categoria = organo.categoria
    if tipo.codigo == "MARCO":
        categorias_marco = {"GOBIERNO_REGIONAL", "ORGANO_MINSA", "UNIVERSIDAD"}
        if categoria not in categorias_marco:
            raise ValidationError(
                "`organo_directorio`: Convenio Marco solo puede ser solicitado por Gobierno Regional, MINSA o Universidad."
            )
        if unidad_ejecutora is not None or facultad is not None:
            raise ValidationError("Convenio Marco no debe llevar `unidad_ejecutora` ni `facultad`.")
        if categoria == "GOBIERNO_REGIONAL" and gobierno_regional is None:
            raise ValidationError("`gobierno_regional` es requerido para Convenio Marco regional.")
        if categoria != "GOBIERNO_REGIONAL" and gobierno_regional is not None:
            raise ValidationError("`gobierno_regional` solo aplica a Convenio Marco de Gobierno Regional.")
    elif tipo.codigo == "ESPECIFICO":
        if categoria != "MINSA_DIRIS" and marco is None:
            raise ValidationError("`convenio_marco` es requerido para Convenio Específico (salvo DIRIS).")
        if unidad_ejecutora is None:
            raise ValidationError("`unidad_ejecutora` es requerida para Convenio Específico.")
        if facultad is None:
            raise ValidationError("`facultad` es requerida para Convenio Específico.")
        if facultad.universidad_id != universidad.id:
            raise ValidationError("`facultad` debe pertenecer a la universidad del convenio (RN-FC-02).")


def _bc_solicitante(tipo_codigo: str, organo: OrganDirectory, unidad_ejecutora):
    """Deriva el solicitante genérico: para Marco → organo_directorio; para Específico → unidad_ejecutora."""
    if tipo_codigo == "MARCO":
        ct = ContentType.objects.get_for_model(OrganDirectory)
        return ct, organo.id
    ct = ContentType.objects.get_for_model(ExecutingUnit)
    return ct, unidad_ejecutora.id


def _bc_mensaje_error(exc: ValidationError) -> str:
    detalle = exc.detail
    if isinstance(detalle, dict):
        return "; ".join(
            f"{k}: {' '.join(map(str, v)) if isinstance(v, list) else v}"
            for k, v in detalle.items()
        )
    if isinstance(detalle, list):
        return " ".join(map(str, detalle))
    return str(detalle)


@transaction.atomic
def _bc_crear_convenio_fila(*, obtener, usuario) -> Convention:
    tipo = _bc_resolver_tipo(obtener("tipo_convenio"))
    titulo = obtener("titulo")
    if not titulo:
        raise ValidationError("`titulo` es requerido.")
    titulo = str(titulo).strip()

    organo = _bc_resolver_organo(obtener("organo_directorio"))
    universidad = _bc_resolver_universidad(obtener("universidad"))
    marco = _bc_resolver_convenio_marco(obtener("convenio_marco"))
    gobierno_regional = _bc_resolver_gobierno_regional(obtener("gobierno_regional"))
    unidad_ejecutora = _bc_resolver_unidad_ejecutora(obtener("unidad_ejecutora"))
    facultad = _bc_resolver_facultad(obtener("facultad"))

    _bc_validar_fila(tipo, organo, marco, gobierno_regional, unidad_ejecutora, facultad, universidad)

    fecha_solicitud = _bc_fecha(obtener("fecha_solicitud"))
    if not fecha_solicitud:
        raise ValidationError("`fecha_solicitud` es requerida.")
    fecha_inicio = _bc_fecha(obtener("fecha_inicio"))
    fecha_fin = _bc_fecha(obtener("fecha_fin"))

    estado_destino_codigo = obtener("estado_destino") or "PUBLICADO"
    estado_destino_codigo = str(estado_destino_codigo).strip().upper()
    if estado_destino_codigo not in _ESTADOS_BULK_PERMITIDOS:
        raise ValidationError(f"`estado_destino` debe ser VIGENTE o PUBLICADO; recibido: {estado_destino_codigo}.")

    nomenclatura = str(obtener("nomenclatura") or "").strip()
    ct_sol, id_sol = _bc_solicitante(tipo.codigo, organo, unidad_ejecutora)

    # Crear directamente en el estado destino (convenio ya suscrito/publicado).
    estado = _obtener_estado(estado_destino_codigo)
    convenio = Convention.objects.create(
        tipo_convenio=tipo,
        convenio_marco=marco,
        nomenclatura=nomenclatura,
        titulo=titulo,
        solicitante_tipo_contenido=ct_sol,
        solicitante_id_objeto=id_sol,
        organo_directorio=organo,
        gobierno_regional=gobierno_regional,
        universidad=universidad,
        unidad_ejecutora=unidad_ejecutora,
        facultad=facultad,
        estado_actual=estado,
        fecha_solicitud=fecha_solicitud,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        creado_por=usuario,
    )
    ConventionStatusHistory.objects.create(
        convenio=convenio, estado=estado, cambiado_por=usuario,
        observacion="Carga masiva — convenio ya suscrito/publicado.",
    )
    registrar_auditoria(usuario, "CREAR", convenio)
    return convenio


@transaction.atomic
def registrar_convenios_masivo(*, archivo, usuario) -> dict:
    """Carga masiva de convenios (Marco y Específico) ya suscritos/publicados.

    Solo disponible para el rol ``Administrador RENADS``. Valida por fila; las
    filas inválidas se reportan sin abortar el lote. Devuelve un resumen:
    ``{creados, omitidos, errores:[{fila, motivo}]}``.
    """
    try:
        wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    except Exception as exc:
        raise ValidationError("No se pudo leer el archivo Excel (.xlsx).") from exc

    ws = wb.active
    filas = ws.iter_rows(values_only=True)
    try:
        cabecera = next(filas)
    except StopIteration as exc:
        raise ValidationError("El archivo está vacío.") from exc

    encabezados = [
        BULK_CONV_ALIAS_COLUMNAS.get(h, h)
        for h in (str(c).strip().lower() if c is not None else "" for c in cabecera)
    ]
    faltantes = BULK_CONV_COLUMNAS_REQUERIDAS - set(encabezados)
    if faltantes:
        raise ValidationError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}.")
    indice = {h: i for i, h in enumerate(encabezados)}

    creados = 0
    errores: list[dict] = []

    for numero_fila, fila in enumerate(filas, start=2):
        if fila is None or all(_bc_celda(v) is None for v in fila):
            continue

        def obtener(col, _fila=fila):
            i = indice.get(col)
            if i is None or i >= len(_fila):
                return None
            return _bc_celda(_fila[i])

        try:
            with transaction.atomic():
                _bc_crear_convenio_fila(obtener=obtener, usuario=usuario)
            creados += 1
        except ValidationError as exc:
            errores.append({"fila": numero_fila, "motivo": _bc_mensaje_error(exc)})
        except Exception as exc:  # noqa: BLE001
            errores.append({"fila": numero_fila, "motivo": str(exc)})

    wb.close()
    return {"creados": creados, "omitidos": len(errores), "errores": errores}


# ---------------------------------------------------------------------------
# Carga masiva de determinación de campos clínicos (solo Administrador RENADS)
# ---------------------------------------------------------------------------
BULK_DET_COLUMNAS_REQUERIDAS = {"ipress", "carrera_profesional", "campos_clinicos_registrados"}
BULK_DET_ALIAS_COLUMNAS = {
    "ipress_id": "ipress",
    "carrera_profesional_id": "carrera_profesional",
    "especialidad_id": "especialidad",
}


def _dm_resolver_convenio(valor) -> Convention:
    if valor is None:
        raise ValidationError("`convenio` es requerido.")
    try:
        return Convention.objects.get(pk=int(str(valor).strip()))
    except (ValueError, Convention.DoesNotExist) as exc:
        raise ValidationError(f"Convenio no encontrado: id={valor}.") from exc


def _dm_resolver_ipress(valor) -> Ipress:
    if valor is None:
        raise ValidationError("`ipress` es requerido.")
    codigo = str(valor).strip()
    try:
        return Ipress.objects.get(codigo_renipress=codigo)
    except Ipress.DoesNotExist as exc:
        raise ValidationError(f"IPRESS no encontrada: {codigo}.") from exc


def _dm_resolver_carrera(valor) -> ProfessionalCareer:
    if valor is None:
        raise ValidationError("`carrera_profesional` es requerida.")
    texto = str(valor).strip()
    if texto.isdigit():
        try:
            return ProfessionalCareer.objects.get(pk=int(texto))
        except ProfessionalCareer.DoesNotExist as exc:
            raise ValidationError(f"Carrera profesional no encontrada: id={texto}.") from exc
    try:
        return ProfessionalCareer.objects.get(nombre__iexact=texto)
    except ProfessionalCareer.DoesNotExist as exc:
        raise ValidationError(f"Carrera profesional no encontrada: {texto}.") from exc
    except ProfessionalCareer.MultipleObjectsReturned as exc:
        raise ValidationError(f"Carrera profesional ambigua (use el id): {texto}.") from exc


def _dm_resolver_especialidad(valor):
    if valor is None or str(valor).strip() == "":
        return None
    texto = str(valor).strip()
    if texto.isdigit():
        try:
            return Specialty.objects.get(pk=int(texto))
        except Specialty.DoesNotExist as exc:
            raise ValidationError(f"Especialidad no encontrada: id={texto}.") from exc
    try:
        return Specialty.objects.get(codigo__iexact=texto)
    except Specialty.DoesNotExist as exc:
        raise ValidationError(f"Especialidad no encontrada: {texto}.") from exc
    except Specialty.MultipleObjectsReturned as exc:
        raise ValidationError(f"Especialidad ambigua (use el id): {texto}.") from exc


@transaction.atomic
def _dm_crear_determinacion_fila(*, obtener, usuario) -> ClinicalFieldRegistration:
    ipress = _dm_resolver_ipress(obtener("ipress"))
    carrera = _dm_resolver_carrera(obtener("carrera_profesional"))
    especialidad = _dm_resolver_especialidad(obtener("especialidad"))

    campos_raw = obtener("campos_clinicos_registrados")
    if campos_raw is None or str(campos_raw).strip() == "":
        raise ValidationError("`campos_clinicos_registrados` es requerido.")
    try:
        campos = int(str(campos_raw).strip())
    except ValueError as exc:
        raise ValidationError("`campos_clinicos_registrados` debe ser un entero.") from exc
    if campos <= 0:
        raise ValidationError("`campos_clinicos_registrados` debe ser un entero positivo.")

    nro_res = str(obtener("numero_resolucion_conapres") or "").strip()
    fecha_res = _bc_fecha(obtener("fecha_resolucion_conapres"))

    datos = {
        "ipress": ipress,
        "carrera_profesional": carrera,
        "especialidad": especialidad,
        "campos_clinicos_registrados": campos,
        "numero_resolucion_conapres": nro_res,
        "fecha_resolucion_conapres": fecha_res,
    }
    return crear_registro_campo_clinico(datos=datos, usuario=usuario)


@transaction.atomic
def registrar_determinacion_masiva(*, archivo, usuario) -> dict:
    """Carga masiva de determinación de campos clínicos (solo Administrador RENADS).

    Cada fila crea un `ClinicalFieldRegistration` vía el service estándar, que
    valida disponibilidad y avanza el convenio al estado correspondiente.
    Devuelve ``{creados, omitidos, errores}``.
    """
    try:
        wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    except Exception as exc:
        raise ValidationError(f"No se pudo leer el archivo Excel: {exc}") from exc

    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        raise ValidationError("El archivo está vacío.")

    cabecera = filas[0]
    filas = filas[1:]
    try:
        encabezados = [
            BULK_DET_ALIAS_COLUMNAS.get(h, h)
            for h in (str(c).strip().lower() if c is not None else "" for c in cabecera)
        ]
    except Exception as exc:
        raise ValidationError("El archivo está vacío.") from exc

    faltantes = BULK_DET_COLUMNAS_REQUERIDAS - set(encabezados)
    if faltantes:
        raise ValidationError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}.")
    indice = {h: i for i, h in enumerate(encabezados)}

    creados = 0
    errores: list[dict] = []

    for numero_fila, fila in enumerate(filas, start=2):
        if fila is None or all(_bc_celda(v) is None for v in fila):
            continue

        def obtener(col, _fila=fila):
            i = indice.get(col)
            if i is None or i >= len(_fila):
                return None
            return _bc_celda(_fila[i])

        try:
            with transaction.atomic():
                _dm_crear_determinacion_fila(obtener=obtener, usuario=usuario)
            creados += 1
        except ValidationError as exc:
            errores.append({"fila": numero_fila, "motivo": _bc_mensaje_error(exc)})
        except Exception as exc:  # noqa: BLE001
            errores.append({"fila": numero_fila, "motivo": str(exc)})

    wb.close()
    return {"creados": creados, "omitidos": len(errores), "errores": errores}


# ---------------------------------------------------------------------------
# Carga masiva de asignación de campos clínicos (solo Administrador RENADS)
# ---------------------------------------------------------------------------
BULK_ASIG_COLUMNAS_REQUERIDAS = {"campo_clinico_ipress", "convenio", "campos_clinicos_autorizados"}
BULK_ASIG_ALIAS_COLUMNAS = {
    "campo_clinico_ipress_id": "campo_clinico_ipress",
    "convenio_id": "convenio",
}


def _asig_resolver_registro(valor) -> ClinicalFieldRegistration:
    if valor is None:
        raise ValidationError("`campo_clinico_ipress` es requerido.")
    try:
        return ClinicalFieldRegistration.objects.get(pk=int(str(valor).strip()))
    except (ValueError, ClinicalFieldRegistration.DoesNotExist) as exc:
        raise ValidationError(f"Registro de campo clínico no encontrado: id={valor}.") from exc


@transaction.atomic
def _asig_crear_asignacion_fila(*, obtener, usuario) -> ClinicalFieldAllocation:
    registro = _asig_resolver_registro(obtener("campo_clinico_ipress"))
    convenio = _dm_resolver_convenio(obtener("convenio"))

    campos_raw = obtener("campos_clinicos_autorizados")
    if campos_raw is None or str(campos_raw).strip() == "":
        raise ValidationError("`campos_clinicos_autorizados` es requerido.")
    try:
        campos = int(str(campos_raw).strip())
    except ValueError as exc:
        raise ValidationError("`campos_clinicos_autorizados` debe ser un entero.") from exc
    if campos <= 0:
        raise ValidationError("`campos_clinicos_autorizados` debe ser un entero positivo.")

    fecha_inicio = _bc_fecha(obtener("fecha_inicio"))
    fecha_fin = _bc_fecha(obtener("fecha_fin"))

    datos = {
        "campo_clinico_ipress": registro,
        "convenio": convenio,
        "campos_clinicos_autorizados": campos,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }
    return crear_asignacion_campo_clinico(datos=datos, usuario=usuario)


@transaction.atomic
def registrar_asignacion_masiva(*, archivo, usuario) -> dict:
    """Carga masiva de asignación de campos clínicos (solo Administrador RENADS).

    Cada fila crea un `ClinicalFieldAllocation` vía el service estándar, que
    valida disponibilidad y coherencia con el convenio. Devuelve ``{creados, omitidos, errores}``.
    """
    try:
        wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    except Exception as exc:
        raise ValidationError(f"No se pudo leer el archivo Excel: {exc}") from exc

    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        raise ValidationError("El archivo está vacío.")

    cabecera = filas[0]
    filas = filas[1:]
    try:
        encabezados = [
            BULK_ASIG_ALIAS_COLUMNAS.get(h, h)
            for h in (str(c).strip().lower() if c is not None else "" for c in cabecera)
        ]
    except Exception as exc:
        raise ValidationError("El archivo está vacío.") from exc

    faltantes = BULK_ASIG_COLUMNAS_REQUERIDAS - set(encabezados)
    if faltantes:
        raise ValidationError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}.")
    indice = {h: i for i, h in enumerate(encabezados)}

    creados = 0
    errores: list[dict] = []

    for numero_fila, fila in enumerate(filas, start=2):
        if fila is None or all(_bc_celda(v) is None for v in fila):
            continue

        def obtener(col, _fila=fila):
            i = indice.get(col)
            if i is None or i >= len(_fila):
                return None
            return _bc_celda(_fila[i])

        try:
            with transaction.atomic():
                _asig_crear_asignacion_fila(obtener=obtener, usuario=usuario)
            creados += 1
        except ValidationError as exc:
            errores.append({"fila": numero_fila, "motivo": _bc_mensaje_error(exc)})
        except Exception as exc:  # noqa: BLE001
            errores.append({"fila": numero_fila, "motivo": str(exc)})

    wb.close()
    return {"creados": creados, "omitidos": len(errores), "errores": errores}
