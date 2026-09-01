"""Refactor de entidades (3/3): schema destructivo final.

Elimina los FK obsoletos de `organo_directorio` (`organo`, `tipo_organo`, `ubigeo`)
y el `referencia_logo`, borra el modelo `OrganType` (tabla `tipo_organo`), fija
`organo_directorio.categoria` como no-nullable (ya poblada en 0029) y finaliza el
refactor de `cargo_ejecutivo` (drop `codigo`, unicidad/orden por `nombre_masculino`).

`DeleteModel OrganType` es seguro aquí: en 0029 las FKs `unidad_ejecutora.tipo_organo`
y `universidad.tipo_entidad` fueron reapuntadas a `organo_directorio`, y `organo_directorio.tipo_organo`
se elimina en este mismo paso; ninguna FK (state ni BD) referencia ya `tipo_organo`.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0029_migrate_and_repoint_organ_types"),
    ]

    operations = [
        # 1-4. Drop de FKs obsoletos y logo de organo_directorio.
        migrations.RemoveField(model_name="organdirectory", name="tipo_organo"),
        migrations.RemoveField(model_name="organdirectory", name="organo"),
        migrations.RemoveField(model_name="organdirectory", name="ubigeo"),
        migrations.RemoveField(model_name="organdirectory", name="referencia_logo"),
        # 5. Borra el modelo/tabla tipo_organo (ya sin referencias FK).
        migrations.DeleteModel(name="OrganType"),
        # 6. categoria → no-nullable (poblada por el backfill de 0029).
        migrations.AlterField(
            model_name="organdirectory",
            name="categoria",
            field=models.CharField(
                verbose_name="categoría",
                max_length=20,
                db_column="categoria",
                choices=[
                    ("ORGANO_MINSA", "Órgano del MINSA"),
                    ("UNIVERSIDAD", "Universidad"),
                    ("GOBIERNO_REGIONAL", "Gobierno Regional"),
                    ("MINSA_DIRIS", "MINSA DIRIS"),
                    ("UNIDAD_EJECUTORA", "Unidad Ejecutora"),
                ],
                help_text="Categoría del órgano (discriminador)",
            ),
        ),
        # 7-9. cargo_ejecutivo: drop codigo, unicidad/orden por nombre_masculino.
        migrations.AlterUniqueTogether(
            name="executiveposition",
            unique_together={("organo", "nombre_masculino")},
        ),
        migrations.RemoveField(model_name="executiveposition", name="codigo"),
        migrations.AlterModelOptions(
            name="executiveposition",
            options={
                "ordering": ["organo", "nombre_masculino"],
                "verbose_name": "cargo ejecutivo",
            },
        ),
    ]
