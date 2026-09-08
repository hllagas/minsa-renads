"""Refactor 1 — FK ``gobierno_regional`` en ``ambito_geografico_sanitario``.

Operaciones:
1. AddField nullable ``gobierno_regional`` en ``HealthGeographicScope``.
2. RunPython backfill: mapea cada ámbito al GORE por coincidencia de nombre de región.

Lógica de mapeo:
- Los nombres de ``ambito_geografico_sanitario`` son nombres cortos de región (p. ej.
  "Amazonas", "Áncash", "Lima (Región)").
- Los nombres de ``gobierno_regional`` siguen el patrón "Gobierno Regional de/del X".
- Para cada ámbito, se normaliza el nombre (lower + strip), se extrae la parte después
  de "gobierno regional de" o "gobierno regional del", y se busca si ese fragmento
  aparece en el nombre del ámbito o viceversa.
- Los 4 DIRIS (nombre contiene "DIRIS" o "Lima Metropolitana") quedan en NULL explícito.
- Si no se encuentra match para un ámbito regional, se deja NULL con warning (no error).
"""

import logging

from django.db import migrations, models
import django.db.models.deletion

logger = logging.getLogger(__name__)


def _normalizar(texto: str) -> str:
    """Normaliza un texto para comparación: lower + strip."""
    return texto.lower().strip()


def _es_diris(nombre: str) -> bool:
    """Devuelve True si el ámbito corresponde a una DIRIS (Lima Metropolitana)."""
    nom = nombre.lower()
    return "diris" in nom or "lima metropolitana" in nom


def poblar_gobierno_regional(apps, schema_editor):
    """Backfill: asigna gobierno_regional_id a cada HealthGeographicScope no-DIRIS."""
    HealthGeographicScope = apps.get_model("convenios", "HealthGeographicScope")
    RegionalGovernment = apps.get_model("convenios", "RegionalGovernment")

    # Construir cache de GORE: clave = nombre de región extraído del nombre del GORE.
    # Patrones: "Gobierno Regional de X" -> "x"; "Gobierno Regional del X" -> "x"
    gore_por_region = {}
    for gore in RegionalGovernment.objects.all():
        nom = _normalizar(gore.nombre)
        # Extraer la parte después de "gobierno regional de " o "gobierno regional del "
        for prefijo in ("gobierno regional del ", "gobierno regional de "):
            if nom.startswith(prefijo):
                region_key = nom[len(prefijo):]
                gore_por_region[region_key] = gore
                break
        else:
            # Sin prefijo estándar (p. ej. "Ministerio de Salud", "Lima Metropolitana")
            gore_por_region[nom] = gore

    for scope in HealthGeographicScope.objects.all():
        if _es_diris(scope.nombre):
            # DIRIS de Lima Metropolitana: gobierno_regional queda NULL
            scope.gobierno_regional_id = None
            scope.save(update_fields=["gobierno_regional_id"])
            continue

        nom_scope = _normalizar(scope.nombre)
        gore_encontrado = None

        # Buscar por coincidencia directa del nombre normalizado del ámbito en el cache.
        if nom_scope in gore_por_region:
            gore_encontrado = gore_por_region[nom_scope]
        else:
            # Búsqueda flexible: el nombre del ámbito está contenido en la clave del
            # GORE o viceversa.
            for region_key, gore in gore_por_region.items():
                if nom_scope in region_key or region_key in nom_scope:
                    gore_encontrado = gore
                    break

        if gore_encontrado is not None:
            scope.gobierno_regional_id = gore_encontrado.pk
            scope.save(update_fields=["gobierno_regional_id"])
        else:
            logger.warning(
                "No se encontró un Gobierno Regional para el ámbito geográfico "
                "sanitario id=%s nombre='%s'. Se deja gobierno_regional_id=NULL. "
                "Corrija manualmente desde el panel de administración.",
                scope.pk,
                scope.nombre,
            )
            scope.gobierno_regional_id = None
            scope.save(update_fields=["gobierno_regional_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0042_executiveposition_organo"),
    ]

    operations = [
        # Paso 1: agregar la columna nullable.
        migrations.AddField(
            model_name="healthgeographicscope",
            name="gobierno_regional",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="gobierno_regional_id",
                related_name="ambitos",
                to="convenios.regionalgovernment",
                help_text=(
                    "Gobierno regional al que corresponde el ámbito sanitario "
                    "(nulo para los 4 DIRIS de Lima Metropolitana)"
                ),
            ),
        ),
        # Paso 2: backfill de datos (reverse noop: no se revierte el backfill).
        migrations.RunPython(poblar_gobierno_regional, reverse_code=migrations.RunPython.noop),
    ]
