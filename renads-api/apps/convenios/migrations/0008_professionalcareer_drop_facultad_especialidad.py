"""Elimina las relaciones `facultad` y `especialidad` de `carrera_profesional`."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0007_ipress_es_sede_docente"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="professionalcareer",
            name="facultad",
        ),
        migrations.RemoveField(
            model_name="professionalcareer",
            name="especialidad",
        ),
    ]
