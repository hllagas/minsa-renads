"""Migración 0027: elimina tutor.ipress_id y crea la tabla tutor_convenio."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0026_student_nota_decimal3"),
        ("convenios", "0050_categoria_rename"),
    ]

    operations = [
        # Paso 1: quitar la columna ipress_id de la tabla tutor.
        migrations.RemoveField(
            model_name="tutor",
            name="ipress",
        ),
        # Paso 2: crear la tabla tutor_convenio.
        migrations.CreateModel(
            name="TutorConvenio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "tutor",
                    models.ForeignKey(
                        db_column="tutor_id",
                        help_text="Tutor",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="convenios_tutor",
                        to="internados.tutor",
                    ),
                ),
                (
                    "convenio",
                    models.ForeignKey(
                        db_column="convenio_id",
                        help_text="Convenio Específico",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tutores_convenio",
                        to="convenios.convention",
                    ),
                ),
                (
                    "ipress",
                    models.ForeignKey(
                        db_column="ipress_id",
                        help_text="Establecimiento (código RENIPRESS de 8 chars, PK textual de ipress)",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tutores_convenio",
                        to="convenios.ipress",
                    ),
                ),
            ],
            options={
                "verbose_name": "convenio del tutor",
                "verbose_name_plural": "convenios del tutor",
                "db_table": "tutor_convenio",
            },
        ),
        migrations.AlterUniqueTogether(
            name="tutorconvenio",
            unique_together={("tutor", "convenio")},
        ),
    ]
