"""Refactor de la PK de ``Ipress`` — parte crítica: promoción del PK + FKs propias + drop ``id``.

Esta migración convierte ``ipress.codigo_renipress`` en la PK textual (varchar 8) y elimina
el ``id`` AutoField, y repunta las 2 FK propias de convenios
(``ClinicalFieldRegistration.ipress``, ``ClinicalFieldAllocation.ipress``) al nuevo PK textual.

Orden de operaciones (ver spec T-08, patrón A→B→C→D de 0045):

PASO A — promocionar codigo_renipress a PK y eliminar el AutoField id:
A1. AlterField codigo_renipress → primary_key=True, serialize=False.
A2. RemoveField Ipress.id (si Django lo requiere tras A1).

PASO B — convertir las columnas transitorias en FK reales al nuevo PK textual:
B1. AlterField ClinicalFieldRegistration.ipress_codigo → FK a convenios.Ipress (PROTECT).
B2. AlterField ClinicalFieldAllocation.ipress_codigo → FK a convenios.Ipress (PROTECT).

PASO C — eliminar las FK enteras y renombrar las transitorias:
C1. RemoveField ClinicalFieldRegistration.ipress (FK int).
C2. RemoveField ClinicalFieldAllocation.ipress (FK int).
C3. RenameField ClinicalFieldRegistration.ipress_codigo → ipress.
C4. RenameField ClinicalFieldAllocation.ipress_codigo → ipress.

PASO D — ajuste final de las FK al db_column canónico ``ipress_id``:
D1. AlterField ClinicalFieldRegistration.ipress → db_column="ipress_id".
D2. AlterField ClinicalFieldAllocation.ipress → db_column="ipress_id".

El unique_together de ClinicalFieldRegistration
(``(convenio, ipress, carrera_profesional, especialidad)``) se preserva porque el campo
``ipress`` conserva su nombre lógico.

Nota SQLite: Django recrea la tabla ``ipress`` automáticamente en el AlterField
primary_key=True / RemoveField id; imita el patrón de 0045.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    # Esta migración elimina el ``id`` AutoField de ``Ipress`` (PASO A). Los backfills
    # transitorios de internados/actividades construyen el mapa ``id entero → codigo_renipress``
    # leyendo la tabla ``ipress`` mientras esta aún conserva su columna ``id``. Por eso deben
    # ejecutarse ANTES de este drop: se declaran como dependencias de 0047 para forzar el orden
    # 0046 → (internados/0021 + actividades/0006) → 0047. En producción (con datos) el mapa sigue
    # siendo construible; sin estas aristas Django ordenaría 0047 primero y el backfill fallaría
    # con AttributeError al no existir ``ip.id``.
    # No introduce ciclo: internados/0022 y actividades/0007 dependen de 0047 (son posteriores),
    # mientras que aquí dependemos solo de los transitorios 0021/0006 (anteriores).
    dependencies = [
        ("convenios", "0046_ipress_pk_renipress_prep"),
        ("internados", "0021_ipress_codigo_transitorio"),
        ("actividades", "0006_ipress_codigo_transitorio"),
    ]

    operations = [
        # ==================================================================
        # PASO A — promocionar codigo_renipress a PK + eliminar id AutoField
        # ==================================================================
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
        migrations.RemoveField(
            model_name="ipress",
            name="id",
        ),

        # ==================================================================
        # PASO B — convertir las columnas transitorias en FK reales al PK textual
        # ==================================================================
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

        # ==================================================================
        # PASO C — eliminar las FK enteras y renombrar las transitorias
        # ==================================================================
        migrations.RemoveField(
            model_name="clinicalfieldregistration",
            name="ipress",
        ),
        migrations.RemoveField(
            model_name="clinicalfieldallocation",
            name="ipress",
        ),
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

        # ==================================================================
        # PASO D — ajuste final de las FK al db_column canónico ipress_id
        # ==================================================================
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
    ]
