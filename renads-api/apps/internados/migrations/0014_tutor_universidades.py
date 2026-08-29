"""RN-24 — Un tutor pertenece de 1 a 2 universidades: tabla puente `tutor_universidad`
y M2M `Tutor.universidades` (el tope de 2 se valida a nivel de aplicación)."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0011_seed_document_type_anexo"),
        ("internados", "0013_internship_estado_declaraciones_seed_grupos"),
    ]

    operations = [
        migrations.CreateModel(
            name="TutorUniversity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "tutor",
                    models.ForeignKey(
                        db_column="tutor_id", help_text="Tutor",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+", to="internados.tutor",
                    ),
                ),
                (
                    "universidad",
                    models.ForeignKey(
                        db_column="universidad_id", help_text="Universidad",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+", to="convenios.university",
                    ),
                ),
            ],
            options={
                "verbose_name": "universidad del tutor",
                "verbose_name_plural": "universidades del tutor",
                "db_table": "tutor_universidad",
                "unique_together": {("tutor", "universidad")},
            },
        ),
        migrations.AddField(
            model_name="tutor",
            name="universidades",
            field=models.ManyToManyField(
                help_text="Universidades a las que pertenece el tutor (de 1 a 2 — RN-24)",
                related_name="tutores", through="internados.TutorUniversity", to="convenios.university",
            ),
        ),
    ]
