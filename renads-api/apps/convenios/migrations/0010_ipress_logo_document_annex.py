"""Estructura de la Etapa 2 (almacenamiento): logo de IPRESS y FK de anexo en documento.

- `AddField Ipress.referencia_logo`: homogeneiza el logo con las otras 4 entidades.
- `AddField Document.documento_anexo`: FK nullable a `internados.AnnexDocument`
  (SET_NULL) que discrimina la cadena de versiones de los anexos por actor.

Depende de la migración de `internados` que crea `AnnexDocument`.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0009_rename_nivel_pregrado"),
        ("internados", "0008_academicperiod_annexdocument_student_fks"),
    ]

    operations = [
        migrations.AddField(
            model_name="ipress",
            name="referencia_logo",
            field=models.CharField(
                blank=True,
                help_text="Referencia externa del logo (repositorio externo)",
                max_length=500,
                verbose_name="referencia del logo",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="documento_anexo",
            field=models.ForeignKey(
                blank=True,
                db_column="documento_anexo_id",
                help_text=(
                    "Anexo (declaración jurada) al que corresponde este documento; "
                    "nulo para documentos que no son anexos"
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="internados.annexdocument",
            ),
        ),
    ]
