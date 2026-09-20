"""Refactor universidad.tipo_entidad: nueva tabla tipo_entidad_universidad.

Pasos:
  1. Crea la tabla `tipo_entidad_universidad` (modelo UniversityEntityType).
  2. Siembra los 4 tipos fijos (seed idempotente vía get_or_create).
  3. Migra datos de universidad.tipo_entidad_id por coincidencia de nombre con
     organo_directorio; default 'Universidad' + warning si no coincide.
  4. Cambia el FK constraint de universidad.tipo_entidad_id para que apunte a
     la nueva tabla (mismo nombre de columna, nuevo destino).
"""

import django.db.models.deletion
from django.db import migrations, models


def seed_tipos(apps, schema_editor):
    """Siembra los 4 tipos fijos de entidad universitaria."""
    UET = apps.get_model("convenios", "UniversityEntityType")
    for nombre in ["Universidad", "Instituto", "Escuela superior", "Escuela de posgrado"]:
        UET.objects.get_or_create(nombre=nombre, defaults={"activo": True})


def migrar_tipo_entidad(apps, schema_editor):
    """Migra universidad.tipo_entidad_id por coincidencia de nombre con organo_directorio."""
    Universidad = apps.get_model("convenios", "University")
    UET = apps.get_model("convenios", "UniversityEntityType")
    OD = apps.get_model("convenios", "OrganDirectory")
    default_tipo = UET.objects.get(nombre="Universidad")
    for univ in Universidad.objects.all():
        od = OD.objects.filter(pk=univ.tipo_entidad_id).first()
        nombre_od = od.nombre if od else None
        nuevo = UET.objects.filter(nombre=nombre_od).first() if nombre_od else None
        if nuevo is None:
            print(
                f"[WARN] Universidad id={univ.pk} nombre={univ.nombre!r}: "
                f"tipo_entidad organo_directorio.nombre={nombre_od!r} sin coincidencia "
                f"-> asignando default 'Universidad'."
            )
            nuevo = default_tipo
        univ.tipo_entidad_id = nuevo.pk
        univ.save(update_fields=["tipo_entidad_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("convenios", "0051_remove_campo_clinico_ipress_convenio"),
    ]

    operations = [
        # Paso 1: Crear tabla tipo_entidad_universidad.
        migrations.CreateModel(
            name="UniversityEntityType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(help_text="Nombre del tipo de entidad universitaria", max_length=100, unique=True, verbose_name="nombre")),
                ("activo", models.BooleanField(default=True, help_text="Indica si el tipo está activo", verbose_name="activo")),
            ],
            options={
                "verbose_name": "tipo de entidad universitaria",
                "verbose_name_plural": "tipos de entidad universitaria",
                "db_table": "tipo_entidad_universidad",
                "ordering": ["id"],
            },
        ),
        # Paso 2: Sembrar los 4 tipos fijos.
        migrations.RunPython(seed_tipos, reverse_code=migrations.RunPython.noop),
        # Paso 3: Migrar datos de universidad.tipo_entidad_id por nombre.
        migrations.RunPython(migrar_tipo_entidad, reverse_code=migrations.RunPython.noop),
        # Paso 4: Cambiar FK constraint de universidad.tipo_entidad para apuntar a la nueva tabla.
        migrations.AlterField(
            model_name="university",
            name="tipo_entidad",
            field=models.ForeignKey(
                db_column="tipo_entidad_id",
                help_text="Tipo de entidad universitaria",
                on_delete=django.db.models.deletion.PROTECT,
                to="convenios.universityentitytype",
            ),
        ),
    ]
