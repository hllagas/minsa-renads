"""Refactor de la PK de ``Ipress`` — parte final (internados): FKs reales + drop enteras.

Repunta las 4 FK de ``Ipress`` en internados al PK textual, elimina las FK enteras y
renombra las columnas transitorias a su nombre canónico. Depende de ``convenios/0047``
(donde ``Ipress`` ya tiene PK textual y sin ``id``).

Orden: B (FK reales sobre transitorias) → C (drop enteras + rename) → D (db_column canónico).
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0021_ipress_codigo_transitorio"),
        ("convenios", "0047_ipress_pk_renipress_promote"),
    ]

    operations = [
        # PASO B — convertir las transitorias en FK reales al PK textual.
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

        # PASO C — eliminar las FK enteras y renombrar las transitorias.
        migrations.RemoveField(
            model_name="internship",
            name="ipress",
        ),
        migrations.RemoveField(
            model_name="rotation",
            name="ipress_origen",
        ),
        migrations.RemoveField(
            model_name="rotation",
            name="ipress_destino",
        ),
        migrations.RemoveField(
            model_name="tutor",
            name="ipress",
        ),
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

        # PASO D — ajuste final al db_column canónico + related_name/on_delete originales.
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
