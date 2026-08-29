"""Carga el catálogo `universidad` desde un archivo Excel (.xlsx).

Pensado para archivos con la estructura oficial de universidades con carreras
de ciencias de la salud licenciadas, con encabezados (fila 1):

    nombre, siglas, codigo_inei, fecha_constitucion, fecha_autorizacion,
    numero_resolucion, direccion_legal, telefono, correo_institucional,
    referencia_logo, activo, tipo_autorizacion_id, tipo_gestion, ubigeo_id,
    tipo_entidad_id

`tipo_gestion` y `tipo_autorizacion_id` vienen como números que reflejan el
orden de siembra de los catálogos en la migración `0002_seed_catalogos`
(1=PUBLICA/2=PRIVADA; 1=LICENCIADA/2=DENEGADA/3=PENDIENTE). `tipo_entidad_id`
usa el mismo orden (1=UNIVERSIDAD/2=ESCUELA_POSGRADO/3=ESCUELA_SUPERIOR/
4=INSTITUTO) pero resuelve contra `tipo_organo` (`OrganType`), el catálogo
unificado de tipos de órgano, filtrado por el órgano "Universidad"
(`0016_unify_organ_types`/`0018_normalize_organ_table`). Los tres también
aceptan texto (el `codigo` del catálogo, p. ej. "PUBLICA").

Prerrequisito: los catálogos `tipo_gestion_universidad`, `tipo_organo`/`organo`
y `tipo_autorizacion` deben estar sembrados (`migrate`) y el catálogo `ubigeo`
cargado (`python manage.py load_ubigeo`) antes de ejecutar este comando.

Uso:
    python manage.py load_universidades --file ruta/al/universidades.xlsx
    python manage.py load_universidades --file universidades.xlsx --dry-run
    python manage.py load_universidades --file universidades.xlsx --sheet Hoja3

Idempotente: re-ejecutar no duplica (clave: `codigo_inei`, o `nombre` si no
tiene código INEI). Las filas ya existentes no se modifican; se reportan como
"existentes". Los errores se reportan por fila sin abortar el lote.
"""

import datetime

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.convenios.models import (
    AuthorizationType,
    Organ,
    OrganType,
    University,
    UniversityManagementType,
    Ubigeo,
)

ORGANO_UNIVERSIDAD = "Universidad"

COLUMNAS_REQUERIDAS = {
    "nombre", "tipo_gestion", "tipo_entidad_id", "tipo_autorizacion_id",
}

# Orden de siembra de los catálogos en 0002_seed_catalogos.py — usado para
# traducir los códigos numéricos del Excel al `codigo` real del catálogo.
ORDEN_TIPO_GESTION = {1: "PUBLICA", 2: "PRIVADA"}
ORDEN_TIPO_ENTIDAD = {
    1: "UNIVERSIDAD", 2: "ESCUELA_POSGRADO", 3: "ESCUELA_SUPERIOR", 4: "INSTITUTO",
}
ORDEN_TIPO_AUTORIZACION = {1: "LICENCIADA", 2: "DENEGADA", 3: "PENDIENTE"}


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
    texto = str(valor).strip()
    if texto.isdigit() and len(texto) == 8:  # formato AAAAMMDD
        try:
            return datetime.date(int(texto[:4]), int(texto[4:6]), int(texto[6:8]))
        except ValueError as exc:
            raise ValueError(f"Fecha inválida: {valor!r}.") from exc
    try:
        return datetime.date.fromisoformat(texto[:10])
    except ValueError as exc:
        raise ValueError(f"Fecha inválida (use AAAAMMDD o AAAA-MM-DD): {valor!r}.") from exc


def _resolver_catalogo(Model, valor, orden, etiqueta):
    if valor is None:
        raise ValueError(f"`{etiqueta}` es requerido.")
    texto = str(valor).strip()
    codigo = orden.get(int(texto)) if texto.isdigit() else texto.upper()
    if codigo is None:
        raise ValueError(f"Valor de `{etiqueta}` no reconocido: {valor!r}.")
    try:
        return Model.objects.get(codigo=codigo)
    except Model.DoesNotExist as exc:
        raise ValueError(f"`{etiqueta}` no encontrado (código={codigo}). ¿Faltan migraciones?") from exc


def _resolver_tipo_entidad(valor):
    if valor is None:
        raise ValueError("`tipo_entidad_id` es requerido.")
    texto = str(valor).strip()
    codigo = ORDEN_TIPO_ENTIDAD.get(int(texto)) if texto.isdigit() else texto.upper()
    if codigo is None:
        raise ValueError(f"Valor de `tipo_entidad_id` no reconocido: {valor!r}.")
    try:
        organo = Organ.objects.get(nombre=ORGANO_UNIVERSIDAD)
    except Organ.DoesNotExist as exc:
        raise ValueError(f"No se encontró el órgano '{ORGANO_UNIVERSIDAD}'. ¿Faltan migraciones?") from exc
    try:
        return OrganType.objects.get(organo=organo, codigo=codigo)
    except OrganType.DoesNotExist as exc:
        raise ValueError(
            f"`tipo_entidad_id` no encontrado (código={codigo}) en el órgano '{ORGANO_UNIVERSIDAD}'."
        ) from exc


def _resolver_ubigeo(valor):
    if valor is None:
        return None
    codigo = str(valor).strip().zfill(6)
    try:
        return Ubigeo.objects.get(codigo=codigo)
    except Ubigeo.DoesNotExist as exc:
        raise ValueError(
            f"UBIGEO no encontrado: {codigo}. Cargue el catálogo con `load_ubigeo` primero."
        ) from exc


def _fila_a_universidad(obtener):
    nombre = obtener("nombre")
    if not nombre:
        raise ValueError("`nombre` es requerido.")

    return {
        "codigo_inei": str(obtener("codigo_inei") or "").strip(),
        "defaults": {
            "nombre": str(nombre).strip(),
            "siglas": str(obtener("siglas") or "").strip(),
            "tipo_gestion": _resolver_catalogo(
                UniversityManagementType, obtener("tipo_gestion"), ORDEN_TIPO_GESTION, "tipo_gestion"
            ),
            "tipo_entidad": _resolver_tipo_entidad(obtener("tipo_entidad_id")),
            "tipo_autorizacion": _resolver_catalogo(
                AuthorizationType, obtener("tipo_autorizacion_id"), ORDEN_TIPO_AUTORIZACION, "tipo_autorizacion_id"
            ),
            "fecha_constitucion": _parse_fecha(obtener("fecha_constitucion")),
            "fecha_autorizacion": _parse_fecha(obtener("fecha_autorizacion")),
            "numero_resolucion": str(obtener("numero_resolucion") or "").strip(),
            "direccion_legal": str(obtener("direccion_legal") or "").strip(),
            "telefono": str(obtener("telefono") or "").strip(),
            "correo_institucional": str(obtener("correo_institucional") or "").strip(),
            "ubigeo": _resolver_ubigeo(obtener("ubigeo_id")),
            # `referencia_logo` es ImageField (subida real) — el Excel no trae
            # una imagen, así que se deja sin asignar; el logo se carga aparte.
            "activo": bool(int(obtener("activo"))) if obtener("activo") is not None else True,
        },
    }


class Command(BaseCommand):
    help = "Carga el catálogo de universidades desde un archivo Excel (.xlsx)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Ruta al archivo .xlsx.")
        parser.add_argument("--sheet", help="Nombre de la hoja (por defecto: la hoja activa).")
        parser.add_argument("--dry-run", action="store_true", help="No escribe en la BD.")

    def handle(self, *args, **opts):
        try:
            wb = openpyxl.load_workbook(opts["file"], read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"No se pudo leer el archivo Excel: {exc}") from exc

        ws = wb[opts["sheet"]] if opts["sheet"] else wb.active
        filas = ws.iter_rows(values_only=True)
        try:
            cabecera = next(filas)
        except StopIteration as exc:
            raise CommandError("El archivo está vacío.") from exc

        encabezados = [str(c).strip().lower() if c is not None else "" for c in cabecera]
        faltan = COLUMNAS_REQUERIDAS - set(encabezados)
        if faltan:
            raise CommandError(
                f"Faltan columnas requeridas: {sorted(faltan)}. Columnas disponibles: {encabezados}."
            )
        indice = {h: i for i, h in enumerate(encabezados)}

        creados = existentes = 0
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
                datos = _fila_a_universidad(obtener)
            except ValueError as exc:
                errores.append({"fila": numero_fila, "motivo": str(exc)})
                continue

            if opts["dry_run"]:
                existe = (
                    University.objects.filter(codigo_inei=datos["codigo_inei"]).exists()
                    if datos["codigo_inei"]
                    else University.objects.filter(nombre=datos["defaults"]["nombre"]).exists()
                )
                existentes += int(existe)
                creados += int(not existe)
                continue

            try:
                with transaction.atomic():  # savepoint por fila
                    if datos["codigo_inei"]:
                        _, creado = University.objects.get_or_create(
                            codigo_inei=datos["codigo_inei"], defaults=datos["defaults"]
                        )
                    else:
                        _, creado = University.objects.get_or_create(
                            nombre=datos["defaults"]["nombre"], defaults=datos["defaults"]
                        )
                creados += int(creado)
                existentes += int(not creado)
            except Exception as exc:  # noqa: BLE001 — reportar sin abortar el lote
                errores.append({"fila": numero_fila, "motivo": str(exc)})

        wb.close()

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {creados} por crear, {existentes} ya existentes, "
                f"{len(errores)} filas con error. No se escribió nada."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Universidades cargadas: {creados} creadas, {existentes} ya existentes, "
                f"{len(errores)} con error. Total en BD: {University.objects.count()}."
            ))

        for error in errores:
            self.stdout.write(self.style.ERROR(f"  Fila {error['fila']}: {error['motivo']}"))
