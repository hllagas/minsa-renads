"""Unificación de cuatro tablas de catálogo de tipo de órgano en una sola tabla `tipo_organo`.

Reemplaza:
- `tipo_entidad_universidad` (UniversityEntityType)
- `tipo_organo_regional`     (RegionalOrganType)
- `tipo_unidad_ejecutora`    (ExecutingUnitType)
- `tipo_organo_minsa`        (MinsaOrganType)

Por la tabla unificada `tipo_organo` (OrganType) con campo discriminador `organo`.

La data migration migra TODOS los registros existentes (incluidos códigos fuera del
seed estándar como MINISTRO, U, U2, etc.) usando get_or_create por (organo, codigo).

Migración irreversible: los DeleteModel finales no tienen reversa útil.
"""

import django.db.models.deletion
from django.db import migrations, models


# ---------------------------------------------------------------------------
# Seed — 14 registros canónicos
# ---------------------------------------------------------------------------
ORGAN_TYPE_SEED = [
    # (organo, codigo, nombre)
    ("UNIVERSIDAD",      "UNIVERSIDAD",             "Universidad"),
    ("UNIVERSIDAD",      "ESCUELA_POSGRADO",        "Escuela de posgrado"),
    ("UNIVERSIDAD",      "ESCUELA_SUPERIOR",        "Escuela superior"),
    ("UNIVERSIDAD",      "INSTITUTO",               "Instituto"),
    ("ORGANO_REGIONAL",  "GERESA",                  "Gerencia Regional de Salud"),
    ("ORGANO_REGIONAL",  "DIRESA",                  "Dirección Regional de Salud"),
    ("ORGANO_REGIONAL",  "DIRIS",                   "Dirección de Redes Integradas de Salud"),
    ("UNIDAD_EJECUTORA", "HOSPITAL",                "Hospital"),
    ("UNIDAD_EJECUTORA", "INSTITUTO_ESPECIALIZADO", "Instituto especializado"),
    ("UNIDAD_EJECUTORA", "RED_SALUD",               "Red de salud"),
    ("MINSA",            "DIGEP",                   "Dirección General de Personal de la Salud"),
    ("MINSA",            "OGAJ",                    "Oficina General de Asesoría Jurídica"),
    ("MINSA",            "SG",                      "Secretaría General"),
    ("MINSA",            "VICEPAS",                 "Despacho Viceministerial de Prestaciones y Aseguramiento en Salud"),
]


def seed_organ_types(apps, schema_editor):
    """Inserta los 14 registros canónicos usando get_or_create."""
    OrganType = apps.get_model("convenios", "OrganType")
    for organo, codigo, nombre in ORGAN_TYPE_SEED:
        OrganType.objects.get_or_create(
            organo=organo,
            codigo=codigo,
            defaults={"nombre": nombre},
        )


def migrar_fks(apps, schema_editor):
    """Mapea las FKs viejas a OrganType por (organo, codigo).

    Para cada categoría, recorre la tabla de catálogo vieja y crea en OrganType
    las entradas que falten (códigos no incluidos en el seed, p. ej. MINISTRO,
    U, U2, etc.). Luego recorre los modelos referenciantes y asigna la FK nueva.
    """
    OrganType = apps.get_model("convenios", "OrganType")

    RegionalOrganType = apps.get_model("convenios", "RegionalOrganType")
    ExecutingUnitType = apps.get_model("convenios", "ExecutingUnitType")
    MinsaOrganType = apps.get_model("convenios", "MinsaOrganType")
    UniversityEntityType = apps.get_model("convenios", "UniversityEntityType")

    RegionalOrgan = apps.get_model("convenios", "RegionalOrgan")
    ExecutingUnit = apps.get_model("convenios", "ExecutingUnit")
    MinsaOrgan = apps.get_model("convenios", "MinsaOrgan")
    University = apps.get_model("convenios", "University")

    # --- Asegurar entradas en OrganType para todos los códigos existentes ---

    for old_obj in RegionalOrganType.objects.all():
        OrganType.objects.get_or_create(
            organo="ORGANO_REGIONAL",
            codigo=old_obj.codigo,
            defaults={"nombre": old_obj.nombre},
        )

    for old_obj in ExecutingUnitType.objects.all():
        OrganType.objects.get_or_create(
            organo="UNIDAD_EJECUTORA",
            codigo=old_obj.codigo,
            defaults={"nombre": old_obj.nombre},
        )

    for old_obj in MinsaOrganType.objects.all():
        OrganType.objects.get_or_create(
            organo="MINSA",
            codigo=old_obj.codigo,
            defaults={"nombre": old_obj.nombre},
        )

    for old_obj in UniversityEntityType.objects.all():
        OrganType.objects.get_or_create(
            organo="UNIVERSIDAD",
            codigo=old_obj.codigo,
            defaults={"nombre": old_obj.nombre},
        )

    # --- Migrar FKs en los modelos referenciantes ---

    for obj in RegionalOrgan.objects.select_related("tipo_organo_regional"):
        new_type = OrganType.objects.get(
            organo="ORGANO_REGIONAL", codigo=obj.tipo_organo_regional.codigo
        )
        obj.tipo_organo_nuevo_id = new_type.pk
        obj.save(update_fields=["tipo_organo_nuevo_id"])

    for obj in ExecutingUnit.objects.select_related("tipo_unidad_ejecutora"):
        new_type = OrganType.objects.get(
            organo="UNIDAD_EJECUTORA", codigo=obj.tipo_unidad_ejecutora.codigo
        )
        obj.tipo_organo_nuevo_id = new_type.pk
        obj.save(update_fields=["tipo_organo_nuevo_id"])

    for obj in MinsaOrgan.objects.select_related("tipo_organo_minsa"):
        new_type = OrganType.objects.get(
            organo="MINSA", codigo=obj.tipo_organo_minsa.codigo
        )
        obj.tipo_organo_nuevo_id = new_type.pk
        obj.save(update_fields=["tipo_organo_nuevo_id"])

    for obj in University.objects.select_related("tipo_entidad"):
        new_type = OrganType.objects.get(
            organo="UNIVERSIDAD", codigo=obj.tipo_entidad.codigo
        )
        obj.tipo_entidad_nuevo_id = new_type.pk
        obj.save(update_fields=["tipo_entidad_nuevo_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0015_clinical_field_registration_allocation"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Paso 1 — Crear el modelo OrganType
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="OrganType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "organo",
                    models.CharField(
                        verbose_name="categoría de órgano",
                        max_length=20,
                        choices=[
                            ("MINSA", "MINSA"),
                            ("UNIVERSIDAD", "Universidad"),
                            ("ORGANO_REGIONAL", "Órgano regional"),
                            ("UNIDAD_EJECUTORA", "Unidad ejecutora"),
                        ],
                        help_text="Categoría del órgano: MINSA, UNIVERSIDAD, ORGANO_REGIONAL o UNIDAD_EJECUTORA",
                    ),
                ),
                (
                    "codigo",
                    models.CharField(
                        verbose_name="código",
                        max_length=50,
                        help_text="Código del tipo (único dentro de la categoría)",
                    ),
                ),
                (
                    "nombre",
                    models.CharField(
                        verbose_name="nombre",
                        max_length=255,
                        help_text="Nombre",
                    ),
                ),
                (
                    "activo",
                    models.BooleanField(
                        verbose_name="activo",
                        default=True,
                        help_text="Indica si está activo",
                    ),
                ),
            ],
            options={
                "verbose_name": "tipo de órgano",
                "verbose_name_plural": "tipos de órgano",
                "db_table": "tipo_organo",
                "ordering": ["organo", "codigo"],
                "unique_together": {("organo", "codigo")},
            },
        ),
        # ----------------------------------------------------------------
        # Paso 2 — Seed de los 14 registros canónicos
        # ----------------------------------------------------------------
        migrations.RunPython(seed_organ_types, migrations.RunPython.noop),
        # ----------------------------------------------------------------
        # Paso 3 — Agregar columnas FK temporales (nullable) en los cuatro modelos
        # ----------------------------------------------------------------
        migrations.AddField(
            model_name="regionalorgan",
            name="tipo_organo_nuevo",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_organo_id_nuevo",
                null=True,
                related_name="+",
            ),
        ),
        migrations.AddField(
            model_name="executingunit",
            name="tipo_organo_nuevo",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_organo_id_nuevo",
                null=True,
                related_name="+",
            ),
        ),
        migrations.AddField(
            model_name="minsaorgan",
            name="tipo_organo_nuevo",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_organo_id_nuevo",
                null=True,
                related_name="+",
            ),
        ),
        migrations.AddField(
            model_name="university",
            name="tipo_entidad_nuevo",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_entidad_id_nuevo",
                null=True,
                related_name="+",
            ),
        ),
        # ----------------------------------------------------------------
        # Paso 4 — Data migration: mapear FK vieja → OrganType
        # ----------------------------------------------------------------
        migrations.RunPython(migrar_fks, migrations.RunPython.noop),
        # ----------------------------------------------------------------
        # Paso 5a — Eliminar columnas viejas
        # ----------------------------------------------------------------
        migrations.RemoveField(model_name="regionalorgan", name="tipo_organo_regional"),
        migrations.RemoveField(model_name="executingunit", name="tipo_unidad_ejecutora"),
        migrations.RemoveField(model_name="minsaorgan", name="tipo_organo_minsa"),
        migrations.RemoveField(model_name="university", name="tipo_entidad"),
        # ----------------------------------------------------------------
        # Paso 5b — Renombrar campos temporales a nombres definitivos
        # ----------------------------------------------------------------
        migrations.RenameField(
            model_name="regionalorgan",
            old_name="tipo_organo_nuevo",
            new_name="tipo_organo",
        ),
        migrations.RenameField(
            model_name="executingunit",
            old_name="tipo_organo_nuevo",
            new_name="tipo_organo",
        ),
        migrations.RenameField(
            model_name="minsaorgan",
            old_name="tipo_organo_nuevo",
            new_name="tipo_organo",
        ),
        migrations.RenameField(
            model_name="university",
            old_name="tipo_entidad_nuevo",
            new_name="tipo_entidad",
        ),
        # ----------------------------------------------------------------
        # Paso 5c — AlterField: quitar null=True y fijar db_column definitivo
        # ----------------------------------------------------------------
        migrations.AlterField(
            model_name="regionalorgan",
            name="tipo_organo",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_organo_id",
                verbose_name="tipo de órgano",
                help_text="GERESA / DIRESA / DIRIS (discriminador: ORGANO_REGIONAL)",
            ),
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="tipo_organo",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_organo_id",
                verbose_name="tipo de órgano",
                help_text="Hospital / Instituto especializado / Red de salud (discriminador: UNIDAD_EJECUTORA)",
            ),
        ),
        migrations.AlterField(
            model_name="minsaorgan",
            name="tipo_organo",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_organo_id",
                verbose_name="tipo de órgano",
                help_text="DIGEP / OGAJ / SG / VICEPAS (discriminador: MINSA)",
            ),
        ),
        migrations.AlterField(
            model_name="university",
            name="tipo_entidad",
            field=models.ForeignKey(
                to="convenios.OrganType",
                on_delete=django.db.models.deletion.PROTECT,
                db_column="tipo_entidad_id",
                verbose_name="tipo de entidad",
                help_text="Universidad / Escuela posgrado / Escuela superior / Instituto (discriminador: UNIVERSIDAD)",
            ),
        ),
        # ----------------------------------------------------------------
        # Paso 6 — Eliminar los cuatro modelos de catálogo viejos
        # ----------------------------------------------------------------
        migrations.DeleteModel(name="UniversityEntityType"),
        migrations.DeleteModel(name="RegionalOrganType"),
        migrations.DeleteModel(name="ExecutingUnitType"),
        migrations.DeleteModel(name="MinsaOrganType"),
    ]
