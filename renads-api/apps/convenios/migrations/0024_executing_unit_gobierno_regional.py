"""`unidad_ejecutora`: estructura final id, codigo, nombre, tipo_organo_id,
gobierno_regional_id, direccion, ubigeo, referencia_logo, activo.

Sustituye `organo_regional` por `gobierno_regional`; reincorpora `codigo` y
`referencia_logo`; `direccion_legal`→`direccion` y `estado`→`activo`.
BD sin datos: sin transferencia.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0023_executing_unit_organo_regional"),
    ]

    operations = [
        migrations.RemoveField(model_name="executingunit", name="organo_regional"),
        migrations.RenameField(
            model_name="executingunit", old_name="direccion_legal", new_name="direccion"
        ),
        migrations.RenameField(
            model_name="executingunit", old_name="estado", new_name="activo"
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="direccion",
            field=models.CharField(
                blank=True, help_text="Dirección", max_length=500, verbose_name="dirección"
            ),
        ),
        migrations.AlterField(
            model_name="executingunit",
            name="activo",
            field=models.BooleanField(default=True, verbose_name="activo"),
        ),
        migrations.AddField(
            model_name="executingunit",
            name="codigo",
            field=models.CharField(
                blank=True, help_text="Código presupuestal", max_length=50, verbose_name="código"
            ),
        ),
        migrations.AddField(
            model_name="executingunit",
            name="referencia_logo",
            field=models.ImageField(
                blank=True, null=True, max_length=500, upload_to="unidad_ejecutora/",
                help_text="Logo institucional (imagen almacenada en el repositorio de medios)",
                verbose_name="logo",
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
