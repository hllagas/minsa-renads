"""Hace obligatoria `universidad_carrera.facultad` (FK NOT NULL).

Antes de aplicar el `NOT NULL` se eliminan las filas legacy sin facultad
(anteriores a la migración 0026, sin facultad reconstruible). Forward-only:
el `reverse` de la limpieza es un noop (no se recrean filas borradas).
"""

from django.db import migrations, models
import django.db.models.deletion


def eliminar_filas_sin_facultad(apps, schema_editor):
    UniversityCareer = apps.get_model("convenios", "UniversityCareer")
    UniversityCareer.objects.filter(facultad__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0031_faculty_direccion"),
    ]

    operations = [
        migrations.RunPython(
            eliminar_filas_sin_facultad, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="universitycareer",
            name="facultad",
            field=models.ForeignKey(
                db_column="facultad_id",
                help_text="Facultad de la universidad a la que pertenece la carrera",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="carreras_facultad",
                to="convenios.faculty",
            ),
        ),
    ]
