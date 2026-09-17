"""Agrega el FK obligatorio `organo` a `cargo_ejecutivo` (`ExecutivePosition`).

Migración de 3 pasos sobre una tabla con datos:

1. ``AddField`` de ``organo`` como **nullable temporal** (para poder crear la columna
   sobre las filas existentes sin violar NOT NULL).
2. ``RunPython`` que **puebla** ``organo_id``:
   - Filas con ``organo_directivo`` no nulo: ``organo_id = organo_directivo.organo_id``.
   - Filas globales (``organo_directivo`` nulo, cargos legacy): se mapean por
     ``nombre_masculino`` → nombre del ``Organ`` canónico. Si algún cargo global no
     matchea el mapeo, la migración **lanza** un error en español (para no dejar nulos
     que romperían el paso 3).
3. ``AlterField`` de ``organo`` a ``null=False`` (estado final del modelo).
"""

from django.db import migrations, models
import django.db.models.deletion


# Mapeo de cargos globales (sin organo_directivo) por nombre_masculino → nombre del Organ.
MAPEO_CARGOS_GLOBALES = {
    # MINSA Administrativo
    "Ministro": "MINSA Administrativo",
    "Viceministro": "MINSA Administrativo",
    "Secretario General": "MINSA Administrativo",
    "Director General": "MINSA Administrativo",
    "Director General de Personal de Salud": "MINSA Administrativo",
    # MINSA DIRIS
    "Director de DIRIS": "MINSA DIRIS",
    # Gobierno Regional
    "Gerente General": "Gobierno Regional",
    "Director Regional de Salud": "Gobierno Regional",
    # Unidad Ejecutora
    "Director de Hospital III": "Unidad Ejecutora",
    # Universidad
    "Rector": "Universidad",
    "Vicerrector": "Universidad",
    "Decano": "Universidad",
}


def poblar_organo(apps, schema_editor):
    """Puebla `organo_id` en `cargo_ejecutivo` (derivación + mapeo de cargos globales)."""
    ExecutivePosition = apps.get_model("convenios", "ExecutivePosition")
    Organ = apps.get_model("convenios", "Organ")

    # Cache de órganos por nombre para no consultar repetidamente.
    organos_por_nombre = {o.nombre: o for o in Organ.objects.all()}

    for cargo in ExecutivePosition.objects.all():
        if cargo.organo_directivo_id is not None:
            # Deriva el órgano del órgano directivo.
            cargo.organo_id = cargo.organo_directivo.organo_id
        else:
            # Cargo global legacy: se mapea por nombre_masculino.
            nombre_organo = MAPEO_CARGOS_GLOBALES.get(cargo.nombre_masculino)
            if nombre_organo is None:
                raise RuntimeError(
                    "No se pudo determinar el órgano para el cargo global "
                    f"'{cargo.nombre_masculino}' (id={cargo.pk}): no está en el mapeo "
                    "de cargos globales. Actualice el mapeo o asigne un organo_directivo "
                    "antes de aplicar la migración."
                )
            organo = organos_por_nombre.get(nombre_organo)
            if organo is None:
                raise RuntimeError(
                    f"El órgano '{nombre_organo}' (mapeado para el cargo global "
                    f"'{cargo.nombre_masculino}', id={cargo.pk}) no existe en la tabla "
                    "`organo`. Verifique los datos del catálogo de órganos."
                )
            cargo.organo_id = organo.pk
        cargo.save(update_fields=["organo"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0041_convention_gobierno_regional_drop_organdirectory_gore"),
    ]

    operations = [
        # Paso 1: agregar la columna como nullable temporal.
        migrations.AddField(
            model_name="executiveposition",
            name="organo",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="organo_id",
                related_name="cargos_ejecutivos",
                to="convenios.organ",
                verbose_name="órgano",
                help_text=(
                    "Categoría de órgano (FK a la tabla canónica `organo`) a la que "
                    "pertenece el cargo; debe coincidir con organo_directivo.organo "
                    "cuando este está seteado"
                ),
            ),
        ),
        # Paso 2: poblar los datos existentes (reverse noop: no se revierte el backfill).
        migrations.RunPython(poblar_organo, reverse_code=migrations.RunPython.noop),
        # Paso 3: hacer la columna obligatoria (estado final del modelo).
        migrations.AlterField(
            model_name="executiveposition",
            name="organo",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="organo_id",
                related_name="cargos_ejecutivos",
                to="convenios.organ",
                verbose_name="órgano",
                help_text=(
                    "Categoría de órgano (FK a la tabla canónica `organo`) a la que "
                    "pertenece el cargo; debe coincidir con organo_directivo.organo "
                    "cuando este está seteado"
                ),
            ),
        ),
    ]
