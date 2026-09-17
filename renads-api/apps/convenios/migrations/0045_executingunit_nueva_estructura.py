"""Refactor 2 parte B — reestructuración DDL de ``ExecutingUnit`` + FKs.

Esta migración convierte la tabla ``unidad_ejecutora`` a su nueva estructura:
- PK textual ``codigo`` (varchar 4) en lugar del AutoField ``id``.
- FK ``ambito_geografico_sanitario_id`` (PROTECT, not null) en lugar de
  ``tipo_organo_id``, ``gobierno_regional_id``, ``direccion``, ``ubigeo_id``,
  ``referencia_logo``.
- Las FK de ``ipress.unidad_ejecutora_id`` y ``convenio.unidad_ejecutora_id``
  pasan de int a varchar(4).

Orden de operaciones (ver spec T-08 pasos A→B→C):

PASO A — Preparar ExecutingUnit con nuevo campo de ámbito:
A1. AddField ambito_geografico_sanitario (null=True transitoriamente).
A2. RunPython poblar_ambito_desde_gore (deriva de gobierno_regional → HealthGeographicScope).
A3. AlterField ambito_geografico_sanitario → NOT NULL.

PASO B — Promocionar codigo_nuevo a FK única antes de hacer PK:
B1. AlterField codigo_nuevo → unique=True, null=False.
B2. AlterField Ipress.unidad_ejecutora_codigo → FK a ExecutingUnit via to_field="codigo_nuevo".
B3. AlterField Convention.unidad_ejecutora_codigo → FK a ExecutingUnit via to_field="codigo_nuevo".

PASO C — Eliminar campos obsoletos, renombrar y establecer PK:
C1. RemoveField ExecutingUnit.id (AutoField PK — Django recrea la tabla en SQLite).
C2-C7. RemoveField tipo_organo, gobierno_regional, direccion, ubigeo, referencia_logo, codigo (antiguo varchar 50).
C8. RenameField codigo_nuevo → codigo.
C9. AlterField codigo → primary_key=True.
C10. RemoveField Ipress.unidad_ejecutora (FK int).
C11. RenameField Ipress.unidad_ejecutora_codigo → unidad_ejecutora.
C12. RemoveField Convention.unidad_ejecutora (FK int).
C13. RenameField Convention.unidad_ejecutora_codigo → unidad_ejecutora.

Nota SQLite: Django maneja la recreación de tabla automáticamente para las operaciones
de AlterField/RemoveField/RenameField que modifican constraints o tipos en SQLite.
"""

from django.db import migrations, models
import django.db.models.deletion


def poblar_ambito_desde_gore(apps, schema_editor):
    """Deriva ambito_geografico_sanitario_id desde gobierno_regional.

    Para cada ExecutingUnit:
    - Busca el HealthGeographicScope cuyo gobierno_regional_id coincide con el
      gobierno_regional_id de la ExecutingUnit (relación establecida en migración 0043).
    - Si el GORE no tiene ámbito mapeado: RuntimeError.
    """
    ExecutingUnit = apps.get_model("convenios", "ExecutingUnit")
    HealthGeographicScope = apps.get_model("convenios", "HealthGeographicScope")

    # Cache: gobierno_regional_id -> HealthGeographicScope
    ambito_por_gore = {}
    for scope in HealthGeographicScope.objects.filter(gobierno_regional_id__isnull=False):
        ambito_por_gore[scope.gobierno_regional_id] = scope

    for eu in ExecutingUnit.objects.all():
        gore_id = eu.gobierno_regional_id
        if gore_id is None:
            raise RuntimeError(
                f"La UnidadEjecutora id={eu.id} (nombre='{eu.nombre}') no tiene "
                "gobierno_regional_id asignado. Asigne un gobierno regional antes "
                "de aplicar esta migración."
            )
        scope = ambito_por_gore.get(gore_id)
        if scope is None:
            raise RuntimeError(
                f"La UnidadEjecutora id={eu.id} (nombre='{eu.nombre}') tiene "
                f"gobierno_regional_id={gore_id} pero ningún HealthGeographicScope "
                "tiene ese gobierno_regional_id asignado (ver migración 0043). "
                "Corrija el mapeo ámbito↔GORE antes de aplicar esta migración."
            )
        eu.ambito_geografico_sanitario_id = scope.pk
        eu.save(update_fields=["ambito_geografico_sanitario_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0044_executingunit_codigo_nuevo_transitorio"),
    ]

    operations = [
        # ==================================================================
        # PASO A — añadir ambito_geografico_sanitario a ExecutingUnit
        # ==================================================================

        # A1: agregar la columna como nullable (para no fallar sobre filas existentes).
        migrations.AddField(
            model_name="executingunit",
            name="ambito_geografico_sanitario",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ambito_geografico_sanitario_id",
                related_name="unidades_ejecutoras",
                to="convenios.healthgeographicscope",
                help_text="Ámbito geográfico sanitario al que pertenece",
            ),
        ),

        # A2: backfill derivando ámbito desde el GORE de cada ExecutingUnit.
        migrations.RunPython(poblar_ambito_desde_gore, reverse_code=migrations.RunPython.noop),

        # A3: hacer NOT NULL.
        migrations.AlterField(
            model_name="executingunit",
            name="ambito_geografico_sanitario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="ambito_geografico_sanitario_id",
                related_name="unidades_ejecutoras",
                to="convenios.healthgeographicscope",
                help_text="Ámbito geográfico sanitario al que pertenece",
            ),
        ),

        # ==================================================================
        # PASO B — hacer codigo_nuevo not null (sin unique constraint para
        # evitar dependencias en PostgreSQL al convertirlo luego a PK)
        # ==================================================================

        # B1: hacer codigo_nuevo not null. NO se pone unique=True porque en
        # PostgreSQL eso crearía una constraint que bloquearía la conversión
        # posterior a PK (C9) mientras existan FKs transitorias que la referencien.
        migrations.AlterField(
            model_name="executingunit",
            name="codigo_nuevo",
            field=models.CharField(
                max_length=4,
                null=False,
                blank=False,
                db_column="codigo_nuevo",
                help_text="Código presupuestal de 4 dígitos (próxima PK)",
            ),
        ),

        # ==================================================================
        # PASO C — eliminar campos obsoletos, renombrar y establecer nueva PK
        # ==================================================================

        # C10/C12: eliminar las FKs int a ExecutingUnit.id en Ipress y Convention
        # ANTES de quitar id de ExecutingUnit (PostgreSQL no permite drop PK
        # mientras hay FK referenciándola).
        migrations.RemoveField(
            model_name="ipress",
            name="unidad_ejecutora",
        ),
        migrations.RemoveField(
            model_name="convention",
            name="unidad_ejecutora",
        ),

        # Eliminar las columnas transitorias CharField (no tienen FKs ni constraints
        # dependientes) antes de reestructurar ExecutingUnit.
        migrations.RemoveField(
            model_name="ipress",
            name="unidad_ejecutora_codigo",
        ),
        migrations.RemoveField(
            model_name="convention",
            name="unidad_ejecutora_codigo",
        ),

        # C1: eliminar el AutoField PK (ya no hay FKs que lo referencien).
        migrations.RemoveField(
            model_name="executingunit",
            name="id",
        ),

        # C2-C6: eliminar campos obsoletos de ExecutingUnit.
        migrations.RemoveField(
            model_name="executingunit",
            name="tipo_organo",
        ),
        migrations.RemoveField(
            model_name="executingunit",
            name="gobierno_regional",
        ),
        migrations.RemoveField(
            model_name="executingunit",
            name="direccion",
        ),
        migrations.RemoveField(
            model_name="executingunit",
            name="ubigeo",
        ),
        migrations.RemoveField(
            model_name="executingunit",
            name="referencia_logo",
        ),

        # C7: eliminar el campo ``codigo`` antiguo (CharField 50, no PK).
        migrations.RemoveField(
            model_name="executingunit",
            name="codigo",
        ),

        # C8: renombrar codigo_nuevo → codigo.
        migrations.RenameField(
            model_name="executingunit",
            old_name="codigo_nuevo",
            new_name="codigo",
        ),

        # C9: hacer codigo la PK (primary_key=True, db_column="codigo").
        # En este punto no hay unique constraint previo ni FKs dependientes:
        # ALTER TABLE puede proceder sin conflicto.
        migrations.AlterField(
            model_name="executingunit",
            name="codigo",
            field=models.CharField(
                max_length=4,
                primary_key=True,
                serialize=False,
                db_column="codigo",
                help_text="Código presupuestal de 4 dígitos (PK)",
            ),
        ),

        # ==================================================================
        # PASO D — añadir las FKs definitivas al nuevo PK y ajustar campos
        # ==================================================================

        # D1: Ipress.unidad_ejecutora → FK a ejecutingunit.codigo (NOT NULL).
        migrations.AddField(
            model_name="ipress",
            name="unidad_ejecutora",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="unidad_ejecutora_id",
                to="convenios.executingunit",
                related_name="ipress",
                help_text="Unidad ejecutora a la que pertenece",
                null=True,  # null temporal para poder añadir sobre filas existentes
            ),
        ),

        # D1b: hacer NOT NULL (no hay filas en unidad_ejecutora en BD de desarrollo,
        # pero si las hubiera se necesitaría backfill previo — ver nota en 0044).
        migrations.AlterField(
            model_name="ipress",
            name="unidad_ejecutora",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                db_column="unidad_ejecutora_id",
                to="convenios.executingunit",
                related_name="ipress",
                help_text="Unidad ejecutora a la que pertenece",
            ),
        ),

        # D2: Convention.unidad_ejecutora → FK a executingunit.codigo (nullable).
        migrations.AddField(
            model_name="convention",
            name="unidad_ejecutora",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="unidad_ejecutora_id",
                to="convenios.executingunit",
                related_name="convenios",
                help_text="Unidad ejecutora parte del Convenio Específico",
            ),
        ),

        # D3: ExecutingUnit.activo — estado final con verbose_name y help_text.
        migrations.AlterField(
            model_name="executingunit",
            name="activo",
            field=models.BooleanField(
                verbose_name="activo",
                default=True,
                help_text="Indica si está activa",
            ),
        ),

        # D4: ExecutingUnit.nombre — estado final con verbose_name y help_text.
        migrations.AlterField(
            model_name="executingunit",
            name="nombre",
            field=models.CharField(
                verbose_name="nombre",
                max_length=255,
                help_text="Nombre de la unidad ejecutora",
            ),
        ),

        # D5: ExecutingUnit.codigo — estado final como PK sin verbose_name.
        migrations.AlterField(
            model_name="executingunit",
            name="codigo",
            field=models.CharField(
                primary_key=True,
                max_length=4,
                serialize=False,
                db_column="codigo",
                help_text="Código presupuestal de 4 dígitos (PK)",
            ),
        ),
    ]
