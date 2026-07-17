"""Agrega `es_sede_docente` a IPRESS (autorización de sede docente por CONAPRES)."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0006_convention_organo_regional_universidad"),
    ]

    operations = [
        migrations.AddField(
            model_name="ipress",
            name="es_sede_docente",
            field=models.BooleanField(
                default=False,
                help_text="Autorizada por CONAPRES como sede docente (asistencial, MINSA/FF.AA.-FF.PP., pública)",
                verbose_name="es sede docente",
            ),
        ),
    ]
