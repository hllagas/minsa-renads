"""Renombra el código del nivel académico `CARRERA_PROFESIONAL` a `PREGRADO`.

Actualiza el registro existente por `codigo` sin borrar la fila, para no romper
las FKs de `ProfessionalCareer`. Idempotente y reversible.
"""

from django.db import migrations


def rename_a_pregrado(apps, schema_editor):
    AcademicLevel = apps.get_model("convenios", "AcademicLevel")
    AcademicLevel.objects.filter(codigo="CARRERA_PROFESIONAL").update(
        codigo="PREGRADO", nombre="Pregrado"
    )


def rename_a_carrera_profesional(apps, schema_editor):
    AcademicLevel = apps.get_model("convenios", "AcademicLevel")
    AcademicLevel.objects.filter(codigo="PREGRADO").update(
        codigo="CARRERA_PROFESIONAL", nombre="Carrera profesional"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0008_professionalcareer_drop_facultad_especialidad"),
    ]

    operations = [
        migrations.RunPython(rename_a_pregrado, rename_a_carrera_profesional),
    ]
