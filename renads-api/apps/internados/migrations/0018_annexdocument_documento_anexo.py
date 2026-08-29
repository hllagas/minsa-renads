"""Renombra `documentos_anexos` → `documento_anexo`, elimina `descripcion` y
permite `tipo_actor` en blanco (absorbe tipos genéricos ANEXO/CONVENIO/RESOLUCION).

BD de desarrollo recreable limpia: no hay transferencia fila por fila.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0017_internship_campo_clinico_allocation"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="annexdocument",
            name="descripcion",
        ),
        migrations.AlterField(
            model_name="annexdocument",
            name="tipo_actor",
            field=models.CharField(
                blank=True,
                choices=[
                    ("INTERNO", "Interno / estudiante"),
                    ("AUTORIDAD_UNIVERSIDAD", "Autoridad de universidad"),
                    ("REPRESENTANTE", "Representante / autoridad (incluye CONAPRES)"),
                ],
                default="INTERNO",
                help_text="Actor que debe presentar el documento (vacío para tipos genéricos)",
                max_length=30,
                verbose_name="tipo de actor",
            ),
        ),
        migrations.AlterModelTable(
            name="annexdocument",
            table="documento_anexo",
        ),
    ]
