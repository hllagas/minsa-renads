"""Refactor de la PK de ``Ipress`` — parte crítica: promoción del PK + FKs propias + drop ``id``.

Esta migración convierte ``ipress.codigo_renipress`` en la PK textual (varchar 8) y elimina
el ``id`` AutoField, y repunta las 2 FK propias de convenios
(``ClinicalFieldRegistration.ipress``, ``ClinicalFieldAllocation.ipress``) al nuevo PK textual.

CORRECCIÓN vs. versión original:
─────────────────────────────────
Django 6.0.6 llama ``check_constraints()`` SIEMPRE al salir del ``SchemaEditor`` (sin condición
``if exc_type is None``). Esto causaba dos fallos encadenados:

1. ``FieldDoesNotExist: NewClinicalFieldRegistration has no field named 'ipress'``
   El ``RemoveField ClinicalFieldRegistration.ipress`` disparaba ``_remake_table`` pero el
   ``unique_together (convenio, ipress, carrera_profesional, especialidad)`` seguía
   referenciando ``ipress``, que ya no existía en el nuevo modelo.

2. ``foreign key mismatch - "interno" referencing "ipress"``
   Al final de 0047 (PK ya varchar), ``PRAGMA foreign_key_check`` detectaba que
   ``interno.ipress_id`` (int) referenciaba ``ipress(id)`` — columna eliminada.

ORDEN CORRECTO DE OPERACIONES:
───────────────────────────────
Paso 0  — limpiar ``unique_together`` (antes de tocar el campo ``ipress``).
Paso pre-A — eliminar las FK enteras de convenios ANTES del cambio de PK, de modo que
             ``campo_clinico_ipress.ipress_id`` y ``campo_clinico_ipress_universidad.ipress_id``
             no referencien ``ipress(id)`` cuando esa columna desaparezca.
Paso A  — promover ``codigo_renipress`` a PK y eliminar ``id``.
Paso B  — convertir las columnas transitorias de convenios en FK reales al PK textual.
Paso C  — renombrar las transitorias al nombre canónico ``ipress``.
Paso D  — ajustar ``db_column`` canónico.
Paso fin — restaurar ``unique_together`` con el campo ya renombrado.

Las FK de internados y actividades se eliminan ANTES en los migrations:
  ``internados/0021b_remove_int_fk_ipress`` y ``actividades/0006b_remove_int_fk_ipress``
(dependencias declaradas abajo). Se reintegran en ``0022`` y ``0007`` tras este migration.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0046_ipress_pk_renipress_prep"),
        # Las FK enteras de internados/actividades deben estar eliminadas ANTES de que
        # este migration elimine ipress.id (o check_constraints detectaría el mismatch).
        ("internados", "0021b_remove_int_fk_ipress"),
        ("actividades", "0006b_remove_int_fk_ipress"),
    ]

    operations = [
        # ======================================================================
        # PASO 0 — limpiar unique_together antes de RemoveField ipress
        # ======================================================================
        migrations.AlterUniqueTogether(
            name="clinicalfieldregistration",
            unique_together=set(),
        ),

        # ======================================================================
        # PASO pre-A — eliminar las FK enteras de convenios ANTES del cambio de PK
        # (Evita que campo_clinico_ipress.ipress_id → ipress(id) quede huérfana
        #  cuando Paso A elimine la columna id de ipress.)
        # ======================================================================
        migrations.RemoveField(
            model_name="clinicalfieldregistration",
            name="ipress",
        ),
        migrations.RemoveField(
            model_name="clinicalfieldallocation",
            name="ipress",
        ),

        # ======================================================================
        # PASO A — eliminar id AutoField + promover codigo_renipress a PK
        # (En PostgreSQL no se puede agregar PK mientras ya existe otra; hay que
        #  quitar id primero. Todas las FK a ipress.id fueron eliminadas en
        #  pre-A y en las dependencias de internados/actividades.)
        # ======================================================================
        migrations.RemoveField(
            model_name="ipress",
            name="id",
        ),
        migrations.AlterField(
            model_name="ipress",
            name="codigo_renipress",
            field=models.CharField(
                verbose_name="código RENIPRESS",
                max_length=8,
                primary_key=True,
                serialize=False,
                help_text="Código RENIPRESS de 8 caracteres (clave primaria)",
            ),
        ),

        # ======================================================================
        # PASO B — convertir las columnas transitorias en FK reales al PK textual
        # ======================================================================
        migrations.AlterField(
            model_name="clinicalfieldregistration",
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
            model_name="clinicalfieldallocation",
            name="ipress_codigo",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_codigo_asig",
                to="convenios.ipress",
                related_name="+",
                help_text="Campo transitorio: FK a la sede por código RENIPRESS",
            ),
        ),

        # ======================================================================
        # PASO C — renombrar las columnas transitorias al nombre canónico
        # ======================================================================
        migrations.RenameField(
            model_name="clinicalfieldregistration",
            old_name="ipress_codigo",
            new_name="ipress",
        ),
        migrations.RenameField(
            model_name="clinicalfieldallocation",
            old_name="ipress_codigo",
            new_name="ipress",
        ),

        # ======================================================================
        # PASO D — ajuste final al db_column canónico ipress_id
        # ======================================================================
        migrations.AlterField(
            model_name="clinicalfieldregistration",
            name="ipress",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_id",
                to="convenios.ipress",
                help_text="Sede docente (establecimiento)",
            ),
        ),
        migrations.AlterField(
            model_name="clinicalfieldallocation",
            name="ipress",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ipress_id",
                to="convenios.ipress",
                help_text="Sede docente (establecimiento)",
            ),
        ),

        # ======================================================================
        # PASO fin — restaurar unique_together con el campo ya renombrado a ipress
        # ======================================================================
        migrations.AlterUniqueTogether(
            name="clinicalfieldregistration",
            unique_together={("convenio", "ipress", "carrera_profesional", "especialidad")},
        ),
    ]
