"""Refactor de la PK de ``Ubigeo`` — promoción del PK + FKs propias (convenios).

Promueve ``ubigeo.codigo`` a PK textual (varchar 6), elimina ``ubigeo.id`` y convierte
las 5 columnas transitorias de convenios en FK reales al nuevo PK.

CORRECCIÓN Django 6.0.6 (misma que 0047 para Ipress):
─────────────────────────────────────────────────────
``check_constraints()`` se llama SIEMPRE al salir del ``SchemaEditor``. Por eso, TODAS
las FK enteras a ``ubigeo(id)`` deben eliminarse ANTES de que este migration corra:
  - Convenios: ``0048b_remove_int_ubigeo_fk``
  - Internados: ``0023b_remove_int_ubigeo_fk``

Tras el PASO A (promoverse PK + eliminar id) no quedan FK columns apuntando a
``ubigeo(id)`` — solo las columnas transitorias ``ubigeo_codigo`` que son CharField sin
FK, por lo que ``PRAGMA foreign_key_check`` no detecta mismatch.

Orden de operaciones:
  PASO A  — promover ``codigo`` a PK + eliminar ``id`` AutoField.
  PASO B  — convertir transitorias en FK reales al PK textual.
  PASO C  — renombrar transitorias al nombre canónico ``ubigeo``.
  PASO D  — ajustar ``db_column`` al canónico ``ubigeo_id``.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0048b_remove_int_ubigeo_fk"),
        # Las FK enteras de internados deben estar eliminadas ANTES de que este
        # migration elimine ubigeo.id.
        ("internados", "0023b_remove_int_ubigeo_fk"),
    ]

    operations = [
        # ======================================================================
        # PASO A — promover codigo a PK textual + eliminar id AutoField
        # ======================================================================
        migrations.AlterField(
            model_name="ubigeo",
            name="codigo",
            field=models.CharField(
                verbose_name="código",
                max_length=6,
                primary_key=True,
                serialize=False,
                help_text="Código UBIGEO INEI (6 dígitos, clave primaria)",
            ),
        ),
        migrations.RemoveField(
            model_name="ubigeo",
            name="id",
        ),

        # ======================================================================
        # PASO B — convertir las columnas transitorias en FK reales al PK textual
        # ======================================================================
        migrations.AlterField(
            model_name="regionalgovernment",
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
            model_name="ipress",
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
            model_name="university",
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
            model_name="faculty",
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
            model_name="universitycampus",
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
        # PASO C — renombrar las transitorias al nombre canónico ``ubigeo``
        # ======================================================================
        migrations.RenameField(model_name="regionalgovernment", old_name="ubigeo_codigo", new_name="ubigeo"),
        migrations.RenameField(model_name="ipress", old_name="ubigeo_codigo", new_name="ubigeo"),
        migrations.RenameField(model_name="university", old_name="ubigeo_codigo", new_name="ubigeo"),
        migrations.RenameField(model_name="faculty", old_name="ubigeo_codigo", new_name="ubigeo"),
        migrations.RenameField(model_name="universitycampus", old_name="ubigeo_codigo", new_name="ubigeo"),

        # ======================================================================
        # PASO D — ajuste final al db_column canónico ``ubigeo_id``
        # ======================================================================
        migrations.AlterField(
            model_name="regionalgovernment",
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
            model_name="ipress",
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
            model_name="university",
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
            model_name="faculty",
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
            model_name="universitycampus",
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
