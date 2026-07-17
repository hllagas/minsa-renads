"""Renombra la FK `interno` → `estudiante` en `actividad_docente_asistencial`
tras el renombrado del modelo en el módulo Internados."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0003_seed_catalogos"),
        ("internados", "0004_rename_student_add_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="teachingactivity", old_name="interno", new_name="estudiante"
        ),
        migrations.AlterField(
            model_name="teachingactivity",
            name="estudiante",
            field=models.ForeignKey(
                db_column="estudiante_id", help_text="Estudiante",
                on_delete=django.db.models.deletion.PROTECT, related_name="actividades",
                to="internados.student",
            ),
        ),
    ]
