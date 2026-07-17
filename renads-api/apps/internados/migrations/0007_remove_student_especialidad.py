"""Elimina el campo `especialidad` del estudiante (ya no aplica)."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0006_rename_internado_to_interno"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="student",
            name="especialidad",
        ),
    ]
