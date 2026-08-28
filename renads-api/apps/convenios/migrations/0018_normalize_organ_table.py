"""Normalización del campo `organo` de `OrganType` en tabla independiente `organo`.

Antes: `tipo_organo.organo` era un CharField con valores
       'MINSA', 'UNIVERSIDAD', 'ORGANO_REGIONAL', 'UNIDAD_EJECUTORA'.

Después: `tipo_organo.organo_id` es FK → nueva tabla `organo`.

Pasos:
1. CreateModel Organ (tabla `organo`).
2. RunPython: seed de 4 registros en `organo`.
3. AddField: columna FK nullable `organo_nuevo_id` en `tipo_organo`.
4. RunPython: data migration — mapea el string viejo al id de `Organ`.
5. AlterUniqueTogether: elimina la restricción (organo, codigo) antes de tocar `organo`.
6. RemoveField: elimina el CharField `organo` viejo.
7. RenameField: `organo_nuevo` → `organo`.
8. AlterField: quita null=True y fija `db_column='organo_id'`.
9. AlterUniqueTogether: reafirma la restricción sobre el campo FK renombrado.
"""

import django.db.models.deletion
from django.db import migrations, models


# ---------------------------------------------------------------------------
# Seed — 4 registros canónicos de Organ
# ---------------------------------------------------------------------------
ORGAN_SEED = [
    "Órgano del MINSA",
    "Universidad",
    "Órgano Regional",
    "Unidad Ejecutora",
]

# Mapa del discriminador string viejo → nombre canónico en Organ
DISCRIMINADOR_MAP = {
    "MINSA": "Órgano del MINSA",
    "UNIVERSIDAD": "Universidad",
    "ORGANO_REGIONAL": "Órgano Regional",
    "UNIDAD_EJECUTORA": "Unidad Ejecutora",
}


def seed_organs(apps, schema_editor):
    """Inserta los 4 registros canónicos en `organo`."""
    Organ = apps.get_model("convenios", "Organ")
    for nombre in ORGAN_SEED:
        Organ.objects.get_or_create(nombre=nombre, defaults={"estado": True})


def migrate_organo_fk(apps, schema_editor):
    """Mapea el CharField discriminador al id de `Organ` correspondiente."""
    Organ = apps.get_model("convenios", "Organ")
    OrganType = apps.get_model("convenios", "OrganType")

    # Construir mapa nombre → instancia Organ
    organ_by_nombre = {obj.nombre: obj for obj in Organ.objects.all()}

    for ot in OrganType.objects.all():
        nombre_organo = DISCRIMINADOR_MAP.get(ot.organo)
        if nombre_organo is None:
            raise ValueError(
                f"OrganType id={ot.pk} tiene discriminador desconocido: '{ot.organo}'"
            )
        organ = organ_by_nombre.get(nombre_organo)
        if organ is None:
            raise ValueError(
                f"No se encontró Organ con nombre '{nombre_organo}' para OrganType id={ot.pk}"
            )
        ot.organo_nuevo_id = organ.pk
        ot.save(update_fields=["organo_nuevo_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0017_alter_executingunit_tipo_organo_and_more"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Paso 1 — Crear el modelo Organ (tabla `organo`)
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="Organ",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "nombre",
                    models.CharField(
                        help_text="Nombre del órgano",
                        max_length=255,
                        verbose_name="nombre",
                    ),
                ),
                (
                    "estado",
                    models.BooleanField(
                        default=True,
                        help_text="Indica si está activo",
                        verbose_name="estado",
                    ),
                ),
            ],
            options={
                "verbose_name": "órgano",
                "verbose_name_plural": "órganos",
                "db_table": "organo",
            },
        ),
        # ----------------------------------------------------------------
        # Paso 2 — Seed de los 4 registros canónicos
        # ----------------------------------------------------------------
        migrations.RunPython(seed_organs, migrations.RunPython.noop),
        # ----------------------------------------------------------------
        # Paso 3 — Agregar columna FK nullable temporal en `tipo_organo`
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name="organtype",
            name="organo_nuevo",
            field=models.ForeignKey(
                to="convenios.Organ",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="organo_nuevo_id",
                null=True,
                related_name="+",
            ),
        ),
        # ----------------------------------------------------------------
        # Paso 4 — Data migration: mapear string → Organ.id
        # ----------------------------------------------------------------
        migrations.RunPython(migrate_organo_fk, migrations.RunPython.noop),
        # ----------------------------------------------------------------
        # Paso 5 — Eliminar unique_together antes de borrar la columna
        #          (SQLite no permite DROP COLUMN con un índice activo)
        # ----------------------------------------------------------------
        migrations.AlterUniqueTogether(
            name="organtype",
            unique_together=set(),
        ),
        # ----------------------------------------------------------------
        # Paso 6 — Eliminar el CharField `organo` viejo
        # ----------------------------------------------------------------
        migrations.RemoveField(
            model_name="organtype",
            name="organo",
        ),
        # ----------------------------------------------------------------
        # Paso 7 — Renombrar `organo_nuevo` → `organo`
        # ----------------------------------------------------------------
        migrations.RenameField(
            model_name="organtype",
            old_name="organo_nuevo",
            new_name="organo",
        ),
        # ----------------------------------------------------------------
        # Paso 8 — AlterField: quitar null, fijar db_column definitivo
        # ----------------------------------------------------------------
        migrations.AlterField(
            model_name="organtype",
            name="organo",
            field=models.ForeignKey(
                to="convenios.Organ",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="organo_id",
                verbose_name="órgano",
                related_name="tipos",
                help_text=(
                    "Categoría del órgano "
                    "(Órgano del MINSA / Universidad / Órgano Regional / Unidad Ejecutora)"
                ),
            ),
        ),
        # ----------------------------------------------------------------
        # Paso 9 — Reafirmar unique_together sobre el campo FK renombrado
        # ----------------------------------------------------------------
        migrations.AlterUniqueTogether(
            name="organtype",
            unique_together={("organo", "codigo")},
        ),
    ]
