"""Renombra la FK `internado` → `interno` en `actividad_docente_asistencial`
tras el renombrado de la tabla en el módulo Internados."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0004_rename_teachingactivity_estudiante"),
        ("internados", "0006_rename_internado_to_interno"),
    ]

    operations = [
        migrations.RenameField(
            model_name="teachingactivity", old_name="internado", new_name="interno"
        ),
        migrations.AlterField(
            model_name="teachingactivity",
            name="interno",
            field=models.ForeignKey(
                db_column="interno_id", help_text="Interno activo",
                on_delete=django.db.models.deletion.PROTECT, related_name="actividades",
                to="internados.internship",
            ),
        ),
    ]
