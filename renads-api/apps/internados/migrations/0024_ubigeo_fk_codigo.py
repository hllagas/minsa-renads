"""Refactor de la PK de ``Ubigeo`` — parte final (internados): FKs reales + rename.

Convierte las columnas transitorias ``ubigeo_codigo`` de ``Student`` y ``Tutor`` en FK
reales al PK textual de ``Ubigeo``, las renombra al nombre canónico y ajusta db_column.

Depende de ``convenios/0049`` (``Ubigeo`` ya tiene PK textual sin ``id``).
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0023b_remove_int_ubigeo_fk"),
        ("convenios", "0049_ubigeo_pk_codigo_promote"),
    ]

    operations = [
        # ======================================================================
        # PASO B — FK reales sobre las columnas transitorias
        # ======================================================================
        migrations.AlterField(
            model_name="student",
            name="ubigeo_codigo",
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ubigeo_codigo",
                to="convenios.ubigeo",
                related_name="+",
                help_text="Campo transitorio: FK a UBIGEO por código",
            ),
        ),
        migrations.AlterField(
            model_name="tutor",
            name="ubigeo_codigo",
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ubigeo_codigo",
                to="convenios.ubigeo",
                related_name="+",
                help_text="Campo transitorio: FK a UBIGEO por código",
            ),
        ),

        # ======================================================================
        # PASO C — renombrar al nombre canónico ``ubigeo``
        # ======================================================================
        migrations.RenameField(model_name="student", old_name="ubigeo_codigo", new_name="ubigeo"),
        migrations.RenameField(model_name="tutor", old_name="ubigeo_codigo", new_name="ubigeo"),

        # ======================================================================
        # PASO D — ajuste final al db_column canónico ``ubigeo_id``
        # ======================================================================
        migrations.AlterField(
            model_name="student",
            name="ubigeo",
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ubigeo_id",
                to="convenios.ubigeo",
                related_name="+",
                help_text="Ubicación geográfica (UBIGEO)",
            ),
        ),
        migrations.AlterField(
            model_name="tutor",
            name="ubigeo",
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ubigeo_id",
                to="convenios.ubigeo",
                related_name="+",
                help_text="Ubicación geográfica (UBIGEO)",
            ),
        ),
    ]
