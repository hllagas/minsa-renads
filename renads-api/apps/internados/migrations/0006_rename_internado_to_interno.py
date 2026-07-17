"""Renombra la tabla `internado` → `interno` (modelo Internship) y las FK
`internado_id` → `interno_id` en historiales y rotación."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0005_seed_parentesco"),
    ]

    operations = [
        # Renombrado de la tabla del internado.
        migrations.AlterModelTable(name="internship", table="interno"),
        migrations.AlterModelOptions(name="internship", options={"verbose_name": "interno"}),
        # related_name de las FK del internado hacia sus entidades padre: internados → internos.
        migrations.AlterField(
            model_name="internship",
            name="estudiante",
            field=models.ForeignKey(
                db_column="estudiante_id", help_text="Estudiante",
                on_delete=django.db.models.deletion.PROTECT, related_name="internos",
                to="internados.student",
            ),
        ),
        migrations.AlterField(
            model_name="internship",
            name="convenio",
            field=models.ForeignKey(
                db_column="convenio_id", help_text="Convenio Específico vigente que lo respalda",
                on_delete=django.db.models.deletion.PROTECT, related_name="internos",
                to="convenios.convention",
            ),
        ),
        migrations.AlterField(
            model_name="internship",
            name="campo_clinico",
            field=models.ForeignKey(
                db_column="campo_clinico_id", help_text="Campo clínico autorizado asignado",
                on_delete=django.db.models.deletion.PROTECT, related_name="internos",
                to="convenios.clinicalfield",
            ),
        ),
        migrations.AlterField(
            model_name="internship",
            name="ipress",
            field=models.ForeignKey(
                db_column="ipress_id", help_text="Sede docente principal",
                on_delete=django.db.models.deletion.PROTECT, related_name="internos_principales",
                to="convenios.ipress",
            ),
        ),
        migrations.AlterField(
            model_name="internship",
            name="tutor",
            field=models.ForeignKey(
                db_column="tutor_id", help_text="Tutor responsable actual",
                on_delete=django.db.models.deletion.PROTECT, related_name="internos",
                to="internados.tutor",
            ),
        ),
        # FK internado → interno en historiales y rotación (atributo + columna).
        migrations.RenameField(
            model_name="internshipstatushistory", old_name="internado", new_name="interno"
        ),
        migrations.AlterField(
            model_name="internshipstatushistory",
            name="interno",
            field=models.ForeignKey(
                db_column="interno_id", help_text="Interno",
                on_delete=django.db.models.deletion.CASCADE, related_name="historial_estados",
                to="internados.internship",
            ),
        ),
        migrations.RenameField(
            model_name="tutorhistory", old_name="internado", new_name="interno"
        ),
        migrations.AlterField(
            model_name="tutorhistory",
            name="interno",
            field=models.ForeignKey(
                db_column="interno_id", help_text="Interno",
                on_delete=django.db.models.deletion.CASCADE, related_name="historial_tutores",
                to="internados.internship",
            ),
        ),
        migrations.RenameField(
            model_name="rotation", old_name="internado", new_name="interno"
        ),
        migrations.AlterField(
            model_name="rotation",
            name="interno",
            field=models.ForeignKey(
                db_column="interno_id", help_text="Interno",
                on_delete=django.db.models.deletion.CASCADE, related_name="rotaciones",
                to="internados.internship",
            ),
        ),
    ]
