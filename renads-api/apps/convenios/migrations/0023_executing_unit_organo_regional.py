"""`unidad_ejecutora`: sustituye `gobierno_regional` por `organo_regional`
(FK → `organo_directorio`, categoría Órgano Regional) y reincorpora `tipo_organo`
(FK → `tipo_organo`, categoría Unidad Ejecutora). BD sin datos: sin transferencia.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0022_refactor_executing_unit"),
    ]

    operations = [
        migrations.RemoveField(model_name="executingunit", name="gobierno_regional"),
        migrations.AddField(
            model_name="executingunit",
            name="organo_regional",
            field=models.ForeignKey(
                null=True, db_column="organo_regional_id",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="unidades_ejecutoras",
                limit_choices_to={"organo__nombre": "Órgano Regional"},
                to="convenios.organdirectory",
                help_text="Órgano regional (GERESA/DIRESA/DIRIS) del directorio al que pertenece",
            ),
        ),
        migrations.AddField(
            model_name="executingunit",
            name="tipo_organo",
            field=models.ForeignKey(
                null=True, db_column="tipo_organo_id",
                on_delete=django.db.models.deletion.PROTECT, related_name="+",
                limit_choices_to={"organo__nombre": "Unidad Ejecutora"},
                to="convenios.organtype",
                help_text="Tipo de unidad ejecutora (Hospital / Instituto especializado / Red de salud; discriminador UNIDAD_EJECUTORA)",
            ),
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="organo_regional",
            field=models.ForeignKey(
                db_column="organo_regional_id",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="unidades_ejecutoras",
                limit_choices_to={"organo__nombre": "Órgano Regional"},
                to="convenios.organdirectory",
                help_text="Órgano regional (GERESA/DIRESA/DIRIS) del directorio al que pertenece",
            ),
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="tipo_organo",
            field=models.ForeignKey(
                db_column="tipo_organo_id",
                on_delete=django.db.models.deletion.PROTECT, related_name="+",
                limit_choices_to={"organo__nombre": "Unidad Ejecutora"},
                to="convenios.organtype",
                help_text="Tipo de unidad ejecutora (Hospital / Instituto especializado / Red de salud; discriminador UNIDAD_EJECUTORA)",
            ),
        ),
    ]
