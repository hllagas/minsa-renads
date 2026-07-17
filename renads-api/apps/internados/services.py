"""Services del módulo Internados: casos de uso de escritura y reglas de negocio (RN).

Toda escritura en `transaction.atomic()`, con auditoría en `bitacora_auditoria` y
registro en el historial de estado correspondiente. Ver §6 del módulo 2.
"""

import datetime
import decimal

import openpyxl
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.common.selectors import usuario_pertenece_a_entidad
from apps.common.services import registrar_auditoria
from apps.convenios.models import ProfessionalCareer, Ubigeo, University
from apps.internados.models import (
    IdentityDocumentType,
    Internship,
    InternshipStatus,
    InternshipStatusHistory,
    RelationshipType,
    Rotation,
    RotationAuthorization,
    RotationStatus,
    RotationStatusHistory,
    Student,
    TutorHistory,
)

# Estados del Convenio Específico que habilitan registrar internados (RN-2/3).
ESTADOS_CONVENIO_VIGENTE = {"VIGENTE", "PUBLICADO", "SUSCRITO"}
MAX_ROTACIONES = 4  # RN-9

# Columnas requeridas del Excel de carga masiva de estudiantes (RN-16, §6 bis schema M2).
CARGA_COLUMNAS_REQUERIDAS = {
    "tipo_documento", "numero_documento", "nombres", "apellido_paterno",
    "universidad", "carrera_profesional",
}


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
        interno=internado, estado=estado, cambiado_por=usuario, observacion=observacion
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
        estudiante=datos["estudiante"],
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
        interno=internado, estado=estado_inicial, cambiado_por=usuario
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
        interno=internado,
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
    # RN-9: máximo 4 rotaciones por estudiante.
    actuales = internado.rotaciones.count()
    if actuales >= MAX_ROTACIONES:
        raise ValidationError(f"El estudiante no puede exceder {MAX_ROTACIONES} rotaciones.")

    estado_inicial = _estado_rotacion("SOLICITADA")
    rotacion = Rotation.objects.create(
        interno=internado,
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
    if participante.convenio_id != rotacion.interno.convenio_id or not participante.es_firmante:
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


# ---------------------------------------------------------------------------
# Prelación (RN-18)
# ---------------------------------------------------------------------------
def estudiantes_por_prelacion(queryset):
    """Ordena estudiantes por orden de mérito: `nota_promedio_ponderado` desc (RN-18).

    Los estudiantes sin nota registrada quedan al final.
    """
    from django.db.models import F

    return queryset.order_by(F("nota_promedio_ponderado").desc(nulls_last=True))


# ---------------------------------------------------------------------------
# Carga masiva de estudiantes (RN-16) — Excel vía openpyxl
# ---------------------------------------------------------------------------
def _celda(valor):
    """Normaliza el valor de una celda: strip de strings, None si vacío."""
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def _parse_fecha(valor):
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


def _resolver_universidad(valor):
    if valor is None:
        raise ValidationError("`universidad` es requerida.")
    texto = str(valor).strip()
    try:
        if texto.isdigit():
            return University.objects.get(id=int(texto))
        return University.objects.get(codigo_inei=texto)
    except University.DoesNotExist as exc:
        raise ValidationError(f"Universidad no encontrada: {texto}.") from exc


def _resolver_carrera(valor, universidad):
    if valor is None:
        raise ValidationError("`carrera_profesional` es requerida.")
    texto = str(valor).strip()
    qs = ProfessionalCareer.objects.filter(facultad__universidad=universidad)
    try:
        carrera = qs.get(id=int(texto)) if texto.isdigit() else qs.get(nombre__iexact=texto)
    except ProfessionalCareer.DoesNotExist as exc:
        raise ValidationError(
            f"Carrera no encontrada en la universidad: {texto}."
        ) from exc
    except ProfessionalCareer.MultipleObjectsReturned as exc:
        raise ValidationError(f"Carrera ambigua (use el id): {texto}.") from exc
    return carrera


def _crear_estudiante_desde_fila(*, obtener, usuario, ct_uni, es_admin) -> Student:
    tipo_doc_codigo = obtener("tipo_documento")
    numero_documento = obtener("numero_documento")
    nombres = obtener("nombres")
    apellido_paterno = obtener("apellido_paterno")
    if not (tipo_doc_codigo and numero_documento and nombres and apellido_paterno):
        raise ValidationError(
            "Campos requeridos: tipo_documento, numero_documento, nombres, apellido_paterno."
        )

    try:
        tipo_doc = IdentityDocumentType.objects.get(codigo=str(tipo_doc_codigo).strip().upper())
    except IdentityDocumentType.DoesNotExist as exc:
        raise ValidationError(f"Tipo de documento inválido: {tipo_doc_codigo}.") from exc

    numero_documento = str(numero_documento).strip()
    if Student.objects.filter(tipo_documento_identidad=tipo_doc, numero_documento=numero_documento).exists():
        raise ValidationError(f"Ya existe un estudiante con {tipo_doc.codigo} {numero_documento}.")

    universidad = _resolver_universidad(obtener("universidad"))
    if not es_admin and not usuario_pertenece_a_entidad(usuario, ct_uni, universidad.id):
        raise ValidationError(
            f"La universidad {universidad.codigo_inei or universidad.id} está fuera de tu ámbito."
        )
    carrera = _resolver_carrera(obtener("carrera_profesional"), universidad)

    ubigeo = None
    ubigeo_codigo = obtener("ubigeo")
    if ubigeo_codigo is not None:
        try:
            ubigeo = Ubigeo.objects.get(codigo=str(ubigeo_codigo).strip())
        except Ubigeo.DoesNotExist as exc:
            raise ValidationError(f"UBIGEO no encontrado: {ubigeo_codigo}.") from exc

    parentesco = None
    parentesco_codigo = obtener("contacto_emergencia_parentesco")
    if parentesco_codigo is not None:
        try:
            parentesco = RelationshipType.objects.get(codigo=str(parentesco_codigo).strip().upper())
        except RelationshipType.DoesNotExist as exc:
            raise ValidationError(f"Parentesco inválido: {parentesco_codigo}.") from exc

    sexo = obtener("sexo")
    if sexo is not None:
        sexo = str(sexo).strip().upper()
        if sexo not in ("M", "F"):
            raise ValidationError("`sexo` debe ser M o F.")

    nota = obtener("nota_promedio_ponderado")
    if nota is not None:
        try:
            nota = decimal.Decimal(str(nota).replace(",", "."))
        except (decimal.InvalidOperation, ValueError) as exc:
            raise ValidationError("`nota_promedio_ponderado` inválida.") from exc

    anio = obtener("anio_academico")
    if anio is not None:
        try:
            anio = int(anio)
        except (TypeError, ValueError) as exc:
            raise ValidationError("`anio_academico` inválido.") from exc

    estudiante = Student.objects.create(
        tipo_documento_identidad=tipo_doc,
        numero_documento=numero_documento,
        nombres=str(nombres).strip(),
        apellido_paterno=str(apellido_paterno).strip(),
        apellido_materno=(str(obtener("apellido_materno")).strip() if obtener("apellido_materno") else ""),
        fecha_nacimiento=_parse_fecha(obtener("fecha_nacimiento")),
        sexo=sexo or "",
        correo=(str(obtener("correo")).strip() if obtener("correo") else ""),
        telefono=(str(obtener("telefono")).strip() if obtener("telefono") else ""),
        direccion=(str(obtener("direccion")).strip() if obtener("direccion") else ""),
        ubigeo=ubigeo,
        universidad=universidad,
        carrera_profesional=carrera,
        codigo_universitario=(str(obtener("codigo_universitario")).strip() if obtener("codigo_universitario") else ""),
        anio_academico=anio,
        nota_promedio_ponderado=nota,
        contacto_emergencia_nombre=(str(obtener("contacto_emergencia_nombre")).strip() if obtener("contacto_emergencia_nombre") else ""),
        contacto_emergencia_telefono=(str(obtener("contacto_emergencia_telefono")).strip() if obtener("contacto_emergencia_telefono") else ""),
        contacto_emergencia_parentesco=parentesco,
        creado_por=usuario,
    )
    registrar_auditoria(usuario, "CREAR", estudiante)
    return estudiante


@transaction.atomic
def registrar_estudiantes_masivo(*, archivo, usuario) -> dict:
    """Carga masiva de estudiantes desde un Excel (.xlsx) — RN-16.

    Valida por fila; las filas inválidas se reportan sin abortar el lote.
    Devuelve un resumen: ``{creados, omitidos, errores:[{fila, motivo}]}``.
    """
    try:
        wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    except Exception as exc:  # archivo corrupto o no .xlsx
        raise ValidationError("No se pudo leer el archivo Excel (.xlsx).") from exc

    ws = wb.active
    filas = ws.iter_rows(values_only=True)
    try:
        cabecera = next(filas)
    except StopIteration as exc:
        raise ValidationError("El archivo está vacío.") from exc

    encabezados = [str(c).strip().lower() if c is not None else "" for c in cabecera]
    faltantes = CARGA_COLUMNAS_REQUERIDAS - set(encabezados)
    if faltantes:
        raise ValidationError(f"Faltan columnas requeridas: {', '.join(sorted(faltantes))}.")
    indice = {h: i for i, h in enumerate(encabezados)}

    ct_uni = ContentType.objects.get_for_model(University).id
    es_admin = usuario.is_superuser or usuario.groups.filter(name="Administrador RENADS").exists()

    creados = 0
    errores: list[dict] = []
    for numero_fila, fila in enumerate(filas, start=2):
        if fila is None or all(_celda(v) is None for v in fila):
            continue  # fila vacía

        def obtener(col, _fila=fila):
            i = indice.get(col)
            if i is None or i >= len(_fila):
                return None
            return _celda(_fila[i])

        try:
            with transaction.atomic():  # savepoint por fila
                _crear_estudiante_desde_fila(
                    obtener=obtener, usuario=usuario, ct_uni=ct_uni, es_admin=es_admin
                )
            creados += 1
        except ValidationError as exc:
            errores.append({"fila": numero_fila, "motivo": _mensaje_error(exc)})
        except Exception as exc:  # noqa: BLE001 — reportar sin abortar el lote
            errores.append({"fila": numero_fila, "motivo": str(exc)})

    wb.close()
    return {"creados": creados, "omitidos": len(errores), "errores": errores}


def _mensaje_error(exc: ValidationError) -> str:
    detalle = exc.detail
    if isinstance(detalle, dict):
        return "; ".join(f"{k}: {' '.join(map(str, v)) if isinstance(v, list) else v}" for k, v in detalle.items())
    if isinstance(detalle, list):
        return " ".join(map(str, detalle))
    return str(detalle)
