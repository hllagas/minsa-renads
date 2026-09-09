"""Carga la tabla `unidad_ejecutora` (ExecutingUnit) desde un archivo Excel.

Estructura esperada del `.xlsx` (encabezados en la primera fila, en cualquier orden):
    nombre | activo | ambito_geografico_sanitario_id | codigo

- `codigo` es la PK textual de 4 caracteres (código presupuestal).
- `ambito_geografico_sanitario_id` es el PK del `HealthGeographicScope` (debe existir en BD).
- `activo` acepta 1/0, true/false, si/no.

Uso:
    python manage.py load_unidades_ejecutoras --file cargas_BD/unidad_ejecutora.xlsx
    python manage.py load_unidades_ejecutoras --file cargas_BD/unidad_ejecutora.xlsx --dry-run

Idempotente: re-ejecutar no duplica (clave: `codigo`); si la fila ya existe, actualiza
`nombre`, `activo` y `ambito_geografico_sanitario`.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.convenios.models import ExecutingUnit, HealthGeographicScope

COLUMNAS = ("nombre", "activo", "ambito_geografico_sanitario_id", "codigo")


def _a_bool(valor):
    """Normaliza el valor de `activo` a booleano."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return bool(int(valor))
    texto = str(valor).strip().lower()
    return texto in {"1", "true", "verdadero", "si", "sí", "x", "activo"}


class Command(BaseCommand):
    help = "Carga la tabla unidad_ejecutora desde un archivo Excel (.xlsx)."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Ruta al archivo .xlsx.")
        parser.add_argument("--dry-run", action="store_true", help="Valida sin escribir en la BD.")

    def handle(self, *args, **opts):
        try:
            import openpyxl
        except ImportError as exc:  # noqa: BLE001
            raise CommandError("Falta la dependencia 'openpyxl' para leer archivos .xlsx.") from exc

        try:
            wb = openpyxl.load_workbook(opts["file"], read_only=True, data_only=True)
        except FileNotFoundError as exc:
            raise CommandError(f"No se encontró el archivo: {opts['file']}.") from exc

        filas = list(wb.active.iter_rows(values_only=True))
        if not filas:
            raise CommandError("El archivo está vacío.")

        encabezado = [str(c).strip() if c is not None else "" for c in filas[0]]
        indices = {}
        for col in COLUMNAS:
            if col not in encabezado:
                raise CommandError(
                    f"Falta la columna '{col}'. Encabezados encontrados: {encabezado}."
                )
            indices[col] = encabezado.index(col)

        # Descarta filas totalmente vacías.
        datos = [r for r in filas[1:] if any(v is not None for v in r)]

        # Cache de ámbitos existentes para validar la FK sin golpear la BD por fila.
        ambitos = set(HealthGeographicScope.objects.values_list("id", flat=True))

        registros = []
        errores = []
        vistos = set()
        for n, fila in enumerate(datos, start=2):  # fila 1 = encabezado
            codigo = str(fila[indices["codigo"]]).strip() if fila[indices["codigo"]] is not None else ""
            nombre = str(fila[indices["nombre"]]).strip() if fila[indices["nombre"]] is not None else ""
            ambito_raw = fila[indices["ambito_geografico_sanitario_id"]]

            if not codigo:
                errores.append(f"Fila {n}: 'codigo' vacío.")
                continue
            if len(codigo) > 4:
                errores.append(f"Fila {n}: 'codigo' '{codigo}' supera 4 caracteres.")
                continue
            if codigo in vistos:
                errores.append(f"Fila {n}: 'codigo' duplicado '{codigo}'.")
                continue
            if not nombre:
                errores.append(f"Fila {n}: 'nombre' vacío (codigo {codigo}).")
                continue
            try:
                ambito_id = int(ambito_raw)
            except (TypeError, ValueError):
                errores.append(f"Fila {n}: 'ambito_geografico_sanitario_id' inválido '{ambito_raw}' (codigo {codigo}).")
                continue
            if ambito_id not in ambitos:
                errores.append(f"Fila {n}: ámbito id={ambito_id} no existe en BD (codigo {codigo}).")
                continue

            vistos.add(codigo)
            registros.append({
                "codigo": codigo,
                "nombre": nombre,
                "activo": _a_bool(fila[indices["activo"]]),
                "ambito_geografico_sanitario_id": ambito_id,
            })

        if errores:
            muestra = "\n".join(errores[:20])
            raise CommandError(
                f"Se encontraron {len(errores)} errores de validación. No se escribió nada.\n{muestra}"
                + ("\n…" if len(errores) > 20 else "")
            )

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {len(registros)} unidades ejecutoras válidas. No se escribió nada."
            ))
            return

        creados = actualizados = 0
        with transaction.atomic():
            for d in registros:
                _, creado = ExecutingUnit.objects.update_or_create(
                    codigo=d["codigo"],
                    defaults={
                        "nombre": d["nombre"],
                        "activo": d["activo"],
                        "ambito_geografico_sanitario_id": d["ambito_geografico_sanitario_id"],
                    },
                )
                creados += int(creado)
                actualizados += int(not creado)

        self.stdout.write(self.style.SUCCESS(
            f"Unidades ejecutoras cargadas: {creados} creadas, {actualizados} actualizadas. "
            f"Total en BD: {ExecutingUnit.objects.count()}."
        ))
