"""Refactor de la PK de ``Ipress`` — parte final (actividades): FK real + drop entera.

Repunta ``TeachingActivity.ipress`` al PK textual, elimina la FK entera y renombra la
columna transitoria a su nombre canónico. Depende de ``convenios/0047``.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0006_ipress_codigo_transitorio"),
        ("convenios", "0047_ipress_pk_renipress_promote"),
    ]

    operations = [
        # PASO B — FK real sobre la transitoria.
        migrations.AlterField(
            model_name="teachingactivity",
            name="ipress_codigo",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_codigo",
                to="convenios.ipress",
                related_name="+",
                help_text="Campo transitorio: FK a la sede por código RENIPRESS",
            ),
        ),

        # PASO C — eliminar la FK entera y renombrar la transitoria.
        migrations.RemoveField(
            model_name="teachingactivity",
            name="ipress",
        ),
        migrations.RenameField(
            model_name="teachingactivity",
            old_name="ipress_codigo",
            new_name="ipress",
        ),

        # PASO D — ajuste final al db_column canónico.
        migrations.AlterField(
            model_name="teachingactivity",
            name="ipress",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_id",
                to="convenios.ipress",
                related_name="actividades",
                help_text="Sede docente",
            ),
        ),
    ]
