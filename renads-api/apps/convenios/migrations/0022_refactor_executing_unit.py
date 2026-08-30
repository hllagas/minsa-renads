"""Refactor de `unidad_ejecutora`: se asocia directamente al gobierno regional.

Campos finales: id, nombre, gobierno_regional_id, direccion_legal, ubigeo, estado.
Se retiran `organo_directorio`, `tipo_organo`, `codigo` y `referencia_logo`;
`direccion`→`direccion_legal` y `activo`→`estado`. BD sin datos: sin transferencia.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0021_university_career"),
    ]

    operations = [
        migrations.RemoveField(model_name="executingunit", name="organo_directorio"),
        migrations.RemoveField(model_name="executingunit", name="tipo_organo"),
        migrations.RemoveField(model_name="executingunit", name="codigo"),
        migrations.RemoveField(model_name="executingunit", name="referencia_logo"),
        migrations.RenameField(
            model_name="executingunit", old_name="direccion", new_name="direccion_legal"
        ),
        migrations.RenameField(
            model_name="executingunit", old_name="activo", new_name="estado"
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="direccion_legal",
            field=models.CharField(
                blank=True, help_text="Dirección legal", max_length=500,
                verbose_name="dirección legal",
            ),
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="estado",
            field=models.BooleanField(
                default=True, help_text="Indica si está activo", verbose_name="estado"
            ),
        ),
        migrations.AddField(
            model_name="executingunit",
            name="gobierno_regional",
            field=models.ForeignKey(
                null=True, db_column="gobierno_regional_id",
                help_text="Gobierno regional al que pertenece",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="unidades_ejecutoras", to="convenios.regionalgovernment",
            ),
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="gobierno_regional",
            field=models.ForeignKey(
                db_column="gobierno_regional_id",
                help_text="Gobierno regional al que pertenece",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="unidades_ejecutoras", to="convenios.regionalgovernment",
            ),
        ),
    ]
