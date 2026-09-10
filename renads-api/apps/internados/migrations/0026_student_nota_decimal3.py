from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0025_refactor_contacto_emergencia_y_tutor_profesion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="nota_promedio_ponderado",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Nota promedio ponderado (escala 0–20, máximo 3 decimales)",
                max_digits=5,
                null=True,
                verbose_name="nota promedio ponderado",
            ),
        ),
    ]
