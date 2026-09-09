"""Refactor de la PK de ``Ipress`` — parte final (actividades): FK real + rename.

Repunta ``TeachingActivity.ipress`` al PK textual, renombrando la columna transitoria.

Nota: la antigua columna FK entera (``ipress_id``) ya fue eliminada por
``0006b_remove_int_fk_ipress``; este migration NO la repite.

Depende de ``convenios/0047``.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0006b_remove_int_fk_ipress"),
        ("convenios", "0047_ipress_pk_renipress_promote"),
    ]

    operations = [
        # ======================================================================
        # PASO B — FK real sobre la transitoria
        # ======================================================================
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

        # ======================================================================
        # PASO C — renombrar la transitoria al nombre canónico
        # (RemoveField de la FK entera ya ejecutado en 0006b)
        # ======================================================================
        migrations.RenameField(
            model_name="teachingactivity",
            old_name="ipress_codigo",
            new_name="ipress",
        ),

        # ======================================================================
        # PASO D — ajuste final al db_column canónico
        # ======================================================================
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
