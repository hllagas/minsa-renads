"""Elimina FK convenio_id de campo_clinico_ipress y ajusta unique_together."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("convenios", "0050_categoria_rename"),
    ]

    operations = [
        # 1. Cambia unique_together: quita convenio de la restricción.
        migrations.AlterUniqueTogether(
            name="clinicalfieldregistration",
            unique_together={("ipress", "carrera_profesional", "especialidad")},
        ),
        # 2. Elimina la FK convenio_id (CASCADE → la columna ya no existe).
        migrations.RemoveField(
            model_name="clinicalfieldregistration",
            name="convenio",
        ),
    ]
