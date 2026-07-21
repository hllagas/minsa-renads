"""Agrega `tipo_actor` a `documentos_anexos` — generaliza el catálogo de documentos
requeridos por actor (interno / autoridad de universidad / representante-CONAPRES)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0009_seed_periodo_anexos"),
    ]

    operations = [
        migrations.AddField(
            model_name="annexdocument",
            name="tipo_actor",
            field=models.CharField(
                choices=[
                    ("INTERNO", "Interno / estudiante"),
                    ("AUTORIDAD_UNIVERSIDAD", "Autoridad de universidad"),
                    ("REPRESENTANTE", "Representante / autoridad (incluye CONAPRES)"),
                ],
                default="INTERNO",
                help_text="Actor que debe presentar el documento",
                max_length=30,
                verbose_name="tipo de actor",
            ),
        ),
    ]
