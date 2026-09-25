"""Carga masiva de la tabla `universidad` desde un archivo Excel (.xlsx).

Estructura esperada (fila 1 = encabezados; una universidad por fila):
    nombre, siglas, codigo_inei, fecha_constitucion, fecha_autorizacion,
    numero_resolucion, direccion_legal, telefono, correo_institucional,
    referencia_logo, activo, tipo_autorizacion_id, tipo_gestion,
    ubigeo_id, tipo_entidad_id

Notas de mapeo:
- `tipo_autorizacion_id`, `tipo_gestion` (→ `tipo_gestion_id`) y `tipo_entidad_id`
  (→ `OrganicUnit`, categoría `UNIVERSIDAD`) son **ids** de catálogo; se validan
  contra la BD. Tras el refactor de entidades, `tipo_entidad_id` debe usar los ids
  de la unidad orgánica (`unidad_organica`, categoría UNIVERSIDAD), no los antiguos de
  `tipo_organo`.
- `ubigeo_id` es el **código INEI** del distrito (no el PK); se resuelve por `Ubigeo.codigo`.
  Si el código no existe, la universidad se carga con `ubigeo` nulo (campo opcional).
- `fecha_*` en formato `YYYYMMDD` (o vacío).
- Idempotente: la clave natural es `nombre` (`update_or_create`); re-ejecutar no duplica.

Uso:
    python manage.py load_universidades --file Universidades.xlsx
    python manage.py load_universidades --file Universidades.xlsx --dry-run
"""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.convenios.models import (
    AuthorizationType,
    OrganicUnit,
    Ubigeo,
    University,
    UniversityManagementType,
)

CAMPOS_TEXTO = [
    "nombre", "siglas", "codigo_inei", "numero_resolucion",
    "direccion_legal", "telefono", "correo_institucional",
]


def _txt(valor):
    return str(valor).strip() if valor is not None else ""


def _fecha(valor):
    """Convierte `YYYYMMDD` (o datetime de Excel) a `date`; vacío → None."""
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    s = str(valor).strip().split(".")[0]  # tolera '20160705.0'
    if len(s) == 8 and s.isdigit():
        return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return None


class Command(BaseCommand):
    help = "Carga masiva de universidades desde un Excel (.xlsx)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Ruta al archivo .xlsx.")
        parser.add_argument("--sheet", help="Nombre de la hoja (por defecto la primera).")
        parser.add_argument("--dry-run", action="store_true", help="No escribe en la BD.")

    def handle(self, *args, **opts):
        try:
            import openpyxl
        except ImportError as exc:  # noqa: BLE001
            raise CommandError("Falta la dependencia 'openpyxl'.") from exc

        try:
            wb = openpyxl.load_workbook(opts["file"], read_only=True, data_only=True)
        except FileNotFoundError as exc:
            raise CommandError(f"No se encontró el archivo: {opts['file']}") from exc

        ws = wb[opts["sheet"]] if opts.get("sheet") else wb.worksheets[0]
        filas = list(ws.iter_rows(values_only=True))
        if len(filas) < 2:
            raise CommandError("El Excel no tiene filas de datos.")

        encabezados = [_txt(h) for h in filas[0]]
        idx = {h: i for i, h in enumerate(encabezados) if h}
        requeridas = {"nombre", "tipo_autorizacion_id", "tipo_gestion", "tipo_entidad_id"}
        faltan = requeridas - set(idx)
        if faltan:
            raise CommandError(
                f"Faltan columnas requeridas: {sorted(faltan)}. Encabezados: {encabezados}"
            )

        # Cachés de catálogos (id → instancia) y ubigeos (codigo → instancia).
        gestiones = {u.id: u for u in UniversityManagementType.objects.all()}
        autorizaciones = {a.id: a for a in AuthorizationType.objects.all()}
        entidades = {o.id: o for o in OrganicUnit.objects.filter(categoria="UNIVERSIDAD")}

        def val(fila, nombre):
            return _txt(fila[idx[nombre]]) if nombre in idx else ""

        def entero(fila, nombre):
            v = val(fila, nombre)
            return int(float(v)) if v else None

        creados = actualizados = omitidos = sin_ubigeo = 0
        errores = []
        pendientes = []

        for n, fila in enumerate(filas[1:], start=2):
            nombre = val(fila, "nombre")
            if not nombre:
                continue  # fila vacía

            gid = entero(fila, "tipo_gestion")
            aid = entero(fila, "tipo_autorizacion_id")
            eid = entero(fila, "tipo_entidad_id")
            if gid not in gestiones:
                errores.append(f"Fila {n} ({nombre}): tipo_gestion id={gid} inexistente.")
                continue
            if aid not in autorizaciones:
                errores.append(f"Fila {n} ({nombre}): tipo_autorizacion_id={aid} inexistente.")
                continue
            if eid not in entidades:
                errores.append(f"Fila {n} ({nombre}): tipo_entidad_id={eid} no es tipo de entidad UNIVERSIDAD del directorio.")
                continue

            ubigeo = None
            cod_ubigeo = val(fila, "ubigeo_id")
            if cod_ubigeo:
                ubigeo = Ubigeo.objects.filter(codigo=cod_ubigeo).first()
                if ubigeo is None:
                    sin_ubigeo += 1

            activo_raw = val(fila, "activo")
            datos = {
                "siglas": val(fila, "siglas"),
                "codigo_inei": val(fila, "codigo_inei"),
                "fecha_constitucion": _fecha(fila[idx["fecha_constitucion"]] if "fecha_constitucion" in idx else None),
                "fecha_autorizacion": _fecha(fila[idx["fecha_autorizacion"]] if "fecha_autorizacion" in idx else None),
                "numero_resolucion": val(fila, "numero_resolucion"),
                "direccion_legal": val(fila, "direccion_legal"),
                "telefono": val(fila, "telefono"),
                "correo_institucional": val(fila, "correo_institucional"),
                "tipo_gestion": gestiones[gid],
                "tipo_autorizacion": autorizaciones[aid],
                "tipo_entidad": entidades[eid],
                "ubigeo": ubigeo,
                "activo": activo_raw in ("", "1", "True", "true", "VERDADERO"),
            }
            pendientes.append((nombre, datos))

        if errores:
            for e in errores:
                self.stdout.write(self.style.ERROR(e))

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {len(pendientes)} universidades válidas, {len(errores)} con error, "
                f"{sin_ubigeo} sin ubigeo. No se escribió nada."
            ))
            return

        with transaction.atomic():
            for nombre, datos in pendientes:
                _, creado = University.objects.update_or_create(nombre=nombre, defaults=datos)
                creados += int(creado)
                actualizados += int(not creado)

        self.stdout.write(self.style.SUCCESS(
            f"Universidades: {creados} creadas, {actualizados} actualizadas, "
            f"{len(errores)} con error (omitidas), {sin_ubigeo} cargadas sin ubigeo. "
            f"Total en BD: {University.objects.count()}."
        ))
