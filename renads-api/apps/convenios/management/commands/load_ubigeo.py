"""Carga el catálogo `ubigeo` (distritos del Perú, INEI) desde un CSV.

Fuentes públicas sugeridas (CSV con código INEI + departamento/provincia/distrito):
- https://raw.githubusercontent.com/geodir/ubigeo-peru/master/geodir-ubigeo-inei.csv
- repos `ernestorivero/Ubigeo-Peru`, `CONCYTEC/ubigeo-peru`.

Uso:
    python manage.py load_ubigeo --file ruta/al/ubigeo.csv
    python manage.py load_ubigeo --url https://.../geodir-ubigeo-inei.csv
    python manage.py load_ubigeo --file ubigeo.csv --dry-run

El comando autodetecta las columnas (código, departamento, provincia, distrito);
se pueden forzar con --col-codigo / --col-departamento / --col-provincia / --col-distrito.
Idempotente: re-ejecutar no duplica (clave: `codigo`).
"""

import csv
import io
import urllib.request

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.convenios.models import Ubigeo

DEFAULT_URL = "https://raw.githubusercontent.com/geodir/ubigeo-peru/master/geodir-ubigeo-inei.csv"

CANDIDATOS = {
    "codigo": ["inei", "ubigeo", "codigo", "cod_ubigeo", "id_ubigeo", "coddist", "iddist"],
    "departamento": ["departamento", "department", "dep", "nombdep", "desc_dep"],
    "provincia": ["provincia", "province", "prov", "nombprov", "desc_prov"],
    "distrito": ["distrito", "district", "dist", "nombdist", "desc_dist", "nombre"],
}


def _detectar(fieldnames, forzado, clave):
    if forzado:
        return forzado
    bajos = {f.lower().strip(): f for f in fieldnames}
    for cand in CANDIDATOS[clave]:
        if cand in bajos:
            return bajos[cand]
    return None


class Command(BaseCommand):
    help = "Carga el catálogo de ubigeos (distritos INEI) desde un CSV local o URL."

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Ruta a un CSV local.")
        parser.add_argument("--url", help=f"URL del CSV (por defecto: {DEFAULT_URL}).")
        parser.add_argument("--dry-run", action="store_true", help="No escribe en la BD.")
        parser.add_argument("--col-codigo")
        parser.add_argument("--col-departamento")
        parser.add_argument("--col-provincia")
        parser.add_argument("--col-distrito")
        parser.add_argument("--delimiter", default=",", help="Delimitador del CSV (por defecto ',').")

    def handle(self, *args, **opts):
        if opts["file"]:
            with open(opts["file"], encoding="utf-8-sig") as fh:
                contenido = fh.read()
        else:
            url = opts["url"] or DEFAULT_URL
            self.stdout.write(f"Descargando {url} …")
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    contenido = resp.read().decode("utf-8-sig")
            except Exception as exc:  # noqa: BLE001
                raise CommandError(f"No se pudo descargar el CSV: {exc}") from exc

        lector = csv.DictReader(io.StringIO(contenido), delimiter=opts["delimiter"])
        if not lector.fieldnames:
            raise CommandError("CSV vacío o sin encabezados.")

        col = {
            c: _detectar(lector.fieldnames, opts[f"col_{c}"], c)
            for c in ("codigo", "departamento", "provincia", "distrito")
        }
        faltan = [c for c, v in col.items() if v is None]
        if faltan:
            raise CommandError(
                f"No se detectaron las columnas {faltan}. Columnas disponibles: {lector.fieldnames}. "
                f"Use --col-<campo> para indicarlas."
            )
        self.stdout.write(f"Columnas: {col}")

        creados = actualizados = omitidos = 0
        filas = []
        for fila in lector:
            codigo = (fila.get(col["codigo"]) or "").strip().zfill(6)
            if len(codigo) != 6 or not codigo.isdigit():
                omitidos += 1
                continue
            filas.append({
                "codigo": codigo,
                "departamento": (fila.get(col["departamento"]) or "").strip(),
                "provincia": (fila.get(col["provincia"]) or "").strip(),
                "distrito": (fila.get(col["distrito"]) or "").strip(),
            })

        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {len(filas)} distritos válidos, {omitidos} filas omitidas. No se escribió nada."
            ))
            return

        with transaction.atomic():
            for d in filas:
                _, creado = Ubigeo.objects.get_or_create(
                    codigo=d["codigo"],
                    defaults={
                        "departamento": d["departamento"],
                        "provincia": d["provincia"],
                        "distrito": d["distrito"],
                    },
                )
                creados += int(creado)
                actualizados += int(not creado)

        self.stdout.write(self.style.SUCCESS(
            f"Ubigeo cargado: {creados} creados, {actualizados} existentes, {omitidos} omitidos. "
            f"Total en BD: {Ubigeo.objects.count()}."
        ))
