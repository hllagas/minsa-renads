"""Refactor de la PK de ``Ipress`` — parte final (internados): FKs reales + rename.

Repunta las 4 columnas transitorias varchar de ``Ipress`` en internados al PK textual,
renombrándolas a sus nombres canónicos y ajustando ``db_column``/``on_delete``.

Nota: las antiguas columnas FK enteras (``ipress_id``, ``ipress_origen_id``,
``ipress_destino_id``) ya fueron eliminadas por el migration anterior
``0021b_remove_int_fk_ipress``; este migration NO las repite.

Depende de ``convenios/0047`` (``Ipress`` ya tiene PK textual sin ``id``).

Orden: B (FK reales sobre transitorias) → C (rename) → D (db_column canónico).
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0021b_remove_int_fk_ipress"),
        ("convenios", "0047_ipress_pk_renipress_promote"),
    ]

    operations = [
        # ======================================================================
        # PASO B — convertir las transitorias en FK reales al PK textual
        # ======================================================================
        migrations.AlterField(
            model_name="internship",
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
        migrations.AlterField(
            model_name="rotation",
            name="ipress_origen_codigo",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_origen_codigo",
                to="convenios.ipress",
                related_name="+",
                help_text="Campo transitorio: FK a la sede de origen por código RENIPRESS",
            ),
        ),
        migrations.AlterField(
            model_name="rotation",
            name="ipress_destino_codigo",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_destino_codigo",
                to="convenios.ipress",
                related_name="+",
                help_text="Campo transitorio: FK a la sede de destino por código RENIPRESS",
            ),
        ),
        migrations.AlterField(
            model_name="tutor",
            name="ipress_codigo",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                db_column="tutor_ipress_codigo",
                to="convenios.ipress",
                related_name="+",
                help_text="Campo transitorio: FK a la sede por código RENIPRESS",
            ),
        ),

        # ======================================================================
        # PASO C — renombrar las transitorias al nombre canónico
        # (RemoveField de las FK enteras ya ejecutado en 0021b)
        # ======================================================================
        migrations.RenameField(
            model_name="internship",
            old_name="ipress_codigo",
            new_name="ipress",
        ),
        migrations.RenameField(
            model_name="rotation",
            old_name="ipress_origen_codigo",
            new_name="ipress_origen",
        ),
        migrations.RenameField(
            model_name="rotation",
            old_name="ipress_destino_codigo",
            new_name="ipress_destino",
        ),
        migrations.RenameField(
            model_name="tutor",
            old_name="ipress_codigo",
            new_name="ipress",
        ),

        # ======================================================================
        # PASO D — ajuste final al db_column canónico + related_name/on_delete originales
        # ======================================================================
        migrations.AlterField(
            model_name="internship",
            name="ipress",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_id",
                to="convenios.ipress",
                related_name="internos_principales",
                help_text="Sede docente principal",
            ),
        ),
        migrations.AlterField(
            model_name="rotation",
            name="ipress_origen",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_origen_id",
                to="convenios.ipress",
                related_name="+",
                help_text="Sede de origen",
            ),
        ),
        migrations.AlterField(
            model_name="rotation",
            name="ipress_destino",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_destino_id",
                to="convenios.ipress",
                related_name="+",
                help_text="Sede de destino",
            ),
        ),
        migrations.AlterField(
            model_name="tutor",
            name="ipress",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                db_column="ipress_id",
                to="convenios.ipress",
                related_name="tutores",
                help_text="Establecimiento al que pertenece",
            ),
        ),
    ]
