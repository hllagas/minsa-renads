"""Carga la tabla `ipress` desde un archivo Excel (.xlsx).

Estructura esperada (encabezados en la primera fila, en cualquier orden):

    Obligatorias
    ────────────
    codigo_renipress          varchar(8) — PK del establecimiento
    nombre                    nombre del establecimiento
    activo                    1/0 o true/false
    ambito_geografico_sanitario_id   id (int) del ámbito sanitario
    unidad_ejecutora_id       código presupuestal (varchar 4) de la UE

    Opcionales
    ──────────
    direccion                 dirección (texto)
    es_sede_docente           1/0 o true/false (default False)
    cantidad_camas            entero positivo
    latitud                   decimal(9,6) como texto o número
    longitud                  decimal(9,6) como texto o número
    numero_ruc                varchar(11)
    categoria_id              id (int) de tipo_categoria
    tipo_clasificacion_id     id (int) de tipo_clasificacion
    microred_id               id (int) de microred
    ubigeo_id                 código UBIGEO (varchar 6)

Notas:
- `referencia_logo` no se carga (requiere subida a storage).
- Idempotente: re-ejecutar actualiza sin duplicar (clave: `codigo_renipress`).

Uso:
    python manage.py load_ipress --file cargas_BD/ipress.xlsx
    python manage.py load_ipress --file cargas_BD/ipress.xlsx --dry-run
"""

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.convenios.models import (
    Category,
    ClassificationType,
    ExecutingUnit,
    HealthGeographicScope,
    Ipress,
    Microred,
    Ubigeo,
)

COLUMNAS_OBLIGATORIAS = (
    "codigo_renipress",
    "nombre",
    "activo",
    "ambito_geografico_sanitario_id",
    "unidad_ejecutora_id",
)

COLUMNAS_OPCIONALES = (
    "direccion",
    "es_sede_docente",
    "cantidad_camas",
    "latitud",
    "longitud",
    "numero_ruc",
    "categoria_id",
    "tipo_clasificacion_id",
    "microred_id",
    "ubigeo_id",
)


def _a_bool(valor, default=False):
    if valor is None:
        return default
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(int(valor))
    return str(valor).strip().lower() in {"1", "true", "verdadero", "si", "sí", "x"}


def _txt(valor):
    return str(valor).strip() if valor is not None else ""


def _int_o_none(valor):
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _decimal_o_none(valor):
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return Decimal(str(valor).strip())
    except InvalidOperation:
        return None


class Command(BaseCommand):
    help = "Carga la tabla ipress desde un archivo Excel (.xlsx)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Ruta al archivo .xlsx.")
        parser.add_argument("--dry-run", action="store_true", help="Valida sin escribir en la BD.")

    def handle(self, *args, **opts):
        try:
            import openpyxl
        except ImportError as exc:
            raise CommandError("Falta la dependencia 'openpyxl' para leer archivos .xlsx.") from exc

        try:
            wb = openpyxl.load_workbook(opts["file"], read_only=True, data_only=True)
        except FileNotFoundError as exc:
            raise CommandError(f"No se encontró el archivo: {opts['file']}.") from exc

        filas = list(wb.active.iter_rows(values_only=True))
        wb.close()
        if not filas:
            raise CommandError("El archivo está vacío.")

        encabezado = [str(c).strip() if c is not None else "" for c in filas[0]]

        for col in COLUMNAS_OBLIGATORIAS:
            if col not in encabezado:
                raise CommandError(
                    f"Falta columna obligatoria '{col}'. Encabezados encontrados: {encabezado}."
                )

        idx = {col: encabezado.index(col) for col in encabezado if col}
        opcionales_presentes = {c for c in COLUMNAS_OPCIONALES if c in idx}

        def val(fila, col, default=None):
            if col not in idx:
                return default
            v = fila[idx[col]]
            return default if v is None else v

        # Cache de claves foráneas válidas
        ambitos = set(HealthGeographicScope.objects.values_list("id", flat=True))
        ues = set(ExecutingUnit.objects.values_list("codigo", flat=True))
        ubigeos = set(Ubigeo.objects.values_list("codigo", flat=True))
        categorias = set(Category.objects.values_list("id", flat=True))
        clasificaciones = set(ClassificationType.objects.values_list("id", flat=True))
        microredes = set(Microred.objects.values_list("id", flat=True))

        datos = [r for r in filas[1:] if any(v is not None for v in r)]

        registros = []
        errores = []
        advertencias = []
        vistos = set()

        for n, fila in enumerate(datos, start=2):
            # ── Campos obligatorios ────────────────────────────────────────────
            codigo = _txt(val(fila, "codigo_renipress"))
            if not codigo:
                errores.append(f"Fila {n}: 'codigo_renipress' vacío.")
                continue
            if len(codigo) > 8:
                errores.append(f"Fila {n}: 'codigo_renipress' '{codigo}' supera 8 caracteres.")
                continue
            if codigo in vistos:
                advertencias.append(f"Fila {n}: 'codigo_renipress' duplicado '{codigo}' — se omite.")
                continue

            nombre = _txt(val(fila, "nombre"))
            if not nombre:
                errores.append(f"Fila {n}: 'nombre' vacío (codigo {codigo}).")
                continue

            ambito_raw = val(fila, "ambito_geografico_sanitario_id")
            try:
                ambito_id = int(ambito_raw)
            except (TypeError, ValueError):
                errores.append(f"Fila {n}: 'ambito_geografico_sanitario_id' inválido '{ambito_raw}' (codigo {codigo}).")
                continue
            if ambito_id not in ambitos:
                errores.append(f"Fila {n}: ámbito id={ambito_id} no existe en BD (codigo {codigo}).")
                continue

            ue_codigo = _txt(val(fila, "unidad_ejecutora_id"))
            if not ue_codigo:
                errores.append(f"Fila {n}: 'unidad_ejecutora_id' vacío (codigo {codigo}).")
                continue
            if ue_codigo not in ues:
                errores.append(f"Fila {n}: unidad_ejecutora '{ue_codigo}' no existe en BD (codigo {codigo}).")
                continue

            # ── Campos opcionales ──────────────────────────────────────────────
            categoria_raw = _int_o_none(val(fila, "categoria_id"))
            if categoria_raw is not None and categoria_raw not in categorias:
                errores.append(f"Fila {n}: categoria_id={categoria_raw} no existe en BD (codigo {codigo}).")
                continue

            clasificacion_raw = _int_o_none(val(fila, "tipo_clasificacion_id"))
            if clasificacion_raw is not None and clasificacion_raw not in clasificaciones:
                errores.append(f"Fila {n}: tipo_clasificacion_id={clasificacion_raw} no existe en BD (codigo {codigo}).")
                continue

            microred_raw = _int_o_none(val(fila, "microred_id"))
            if microred_raw is not None and microred_raw not in microredes:
                errores.append(f"Fila {n}: microred_id={microred_raw} no existe en BD (codigo {codigo}).")
                continue

            ubigeo_raw = _txt(val(fila, "ubigeo_id")) or None
            if ubigeo_raw is not None and ubigeo_raw not in ubigeos:
                advertencias.append(
                    f"Fila {n}: ubigeo '{ubigeo_raw}' no existe en BD (codigo {codigo}) — se carga con ubigeo nulo."
                )
                ubigeo_raw = None

            vistos.add(codigo)
            registros.append({
                "codigo_renipress": codigo,
                "nombre": nombre,
                "activo": _a_bool(val(fila, "activo"), default=True),
                "ambito_geografico_sanitario_id": ambito_id,
                "unidad_ejecutora_id": ue_codigo,
                "direccion": _txt(val(fila, "direccion")),
                "es_sede_docente": _a_bool(val(fila, "es_sede_docente"), default=False),
                "cantidad_camas": _int_o_none(val(fila, "cantidad_camas")),
                "latitud": _decimal_o_none(val(fila, "latitud")),
                "longitud": _decimal_o_none(val(fila, "longitud")),
                "numero_ruc": _txt(val(fila, "numero_ruc")),
                "categoria_id": categoria_raw,
                "tipo_clasificacion_id": clasificacion_raw,
                "microred_id": microred_raw,
                "ubigeo_id": ubigeo_raw,
            })

        for adv in advertencias:
            self.stdout.write(self.style.WARNING(f"ADVERTENCIA: {adv}"))

        if errores:
            muestra = "\n".join(errores[:30])
            raise CommandError(
                f"Se encontraron {len(errores)} errores de validación. No se escribió nada.\n{muestra}"
                + ("\n…" if len(errores) > 30 else "")
            )

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {len(registros)} registros válidos, {len(advertencias)} advertencias, "
                f"{len(datos) - len(registros)} omitidos. No se escribió nada."
            ))
            return

        creados = actualizados = 0
        with transaction.atomic():
            for d in registros:
                codigo = d.pop("codigo_renipress")
                _, creado = Ipress.objects.update_or_create(
                    codigo_renipress=codigo,
                    defaults=d,
                )
                creados += int(creado)
                actualizados += int(not creado)

        self.stdout.write(self.style.SUCCESS(
            f"IPRESS cargadas: {creados} creadas, {actualizados} actualizadas. "
            f"Total en BD: {Ipress.objects.count()}."
        ))
