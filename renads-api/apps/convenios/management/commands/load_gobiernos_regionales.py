"""Carga los gobiernos regionales del Perú (uno por región), asociados a `region`.

Los 25 gobiernos regionales se derivan del catálogo `region` ya sembrado: por cada
región se crea un `gobierno_regional` con nombre oficial «Gobierno Regional de/del
<Región>». Idempotente (clave natural: `region`); re-ejecutar no duplica.

Los campos `ubigeo` y `sigla` de `gobierno_regional` son opcionales y este comando
no los siembra (se dejan nulos/vacíos); pueden completarse luego vía el CRUD.

Uso:
    python manage.py load_gobiernos_regionales
    python manage.py load_gobiernos_regionales --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.convenios.models import Region, RegionalGovernment

# Regiones cuyo nombre oficial usa «del» en lugar de «de».
USA_DEL = {"Callao", "Cusco"}


def _nombre_gore(region_nombre: str) -> str:
    conector = "del" if region_nombre in USA_DEL else "de"
    return f"Gobierno Regional {conector} {region_nombre}"


class Command(BaseCommand):
    help = "Carga los gobiernos regionales del Perú (uno por región)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="No escribe en la BD.")

    def handle(self, *args, **opts):
        regiones = list(Region.objects.order_by("codigo"))
        if not regiones:
            self.stdout.write(self.style.ERROR(
                "No hay regiones sembradas; ejecuta primero el seed de catálogos."
            ))
            return

        if opts["dry_run"]:
            for r in regiones:
                self.stdout.write(f"[dry-run] {_nombre_gore(r.nombre)}  → región {r.nombre}")
            self.stdout.write(self.style.WARNING(
                f"[dry-run] {len(regiones)} gobiernos regionales. No se escribió nada."
            ))
            return

        creados = actualizados = 0
        with transaction.atomic():
            for r in regiones:
                _, creado = RegionalGovernment.objects.update_or_create(
                    region=r, defaults={"nombre": _nombre_gore(r.nombre), "activo": True},
                )
                creados += int(creado)
                actualizados += int(not creado)

        self.stdout.write(self.style.SUCCESS(
            f"Gobiernos regionales: {creados} creados, {actualizados} actualizados. "
            f"Total en BD: {RegionalGovernment.objects.count()}."
        ))
