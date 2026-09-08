"""Refactor 2 parte A — columnas transitorias + backfill para ``ExecutingUnit``.

ANÁLISIS DE DATOS PREVIO A LA MIGRACIÓN (T-05):
================================================
Consulta ejecutada: ``ExecutingUnit.objects.count()`` → 0 filas.

La tabla ``unidad_ejecutora`` no tiene datos en la BD de desarrollo.

Implicaciones:
- No hay filas que backfillar en ninguna de las funciones RunPython de esta migración.
- No hay riesgo de colisión de ``codigo_nuevo``.
- No hay ``Ipress`` ni ``Convention`` con ``unidad_ejecutora_id`` (ambas FKs quedan
  vacías / NULL en la BD actual — las columnas transitorias se crearán con
  NULL en todas las filas existentes de ``ipress`` y ``convenio``).

Operaciones de esta migración:
1. AddField ``ExecutingUnit.codigo_nuevo`` — CharField(4, null=True, transitorio).
2. RunPython ``poblar_codigo_nuevo`` — backfill (noop real por 0 filas).
3. AddField ``Ipress.unidad_ejecutora_codigo`` — transitorio, db_column distinto.
4. RunPython ``poblar_ipress_codigo`` — backfill (noop real por 0 filas con UE).
5. AddField ``Convention.unidad_ejecutora_codigo`` — transitorio, db_column distinto.
6. RunPython ``poblar_convenio_codigo`` — backfill (noop real por 0 filas con UE).
"""

from django.db import migrations, models


def poblar_codigo_nuevo(apps, schema_editor):
    """Backfill de codigo_nuevo en ExecutingUnit.

    Reglas:
    - Si ``codigo`` no está vacío y ``len(codigo) <= 4``: zero-pad a 4 chars.
    - Si ``codigo`` tiene más de 4 chars o está vacío: usar ``f"{id:04d}"``.
    - Si ``f"{id:04d}"`` colisiona con un ``codigo_nuevo`` ya asignado: RuntimeError.
    - Verificación final de unicidad.
    """
    ExecutingUnit = apps.get_model("convenios", "ExecutingUnit")

    asignados = {}  # codigo_nuevo -> id de la fila

    for eu in ExecutingUnit.objects.all():
        codigo_original = (eu.codigo or "").strip()
        if codigo_original and len(codigo_original) <= 4:
            codigo_nuevo = codigo_original.zfill(4)
        else:
            codigo_nuevo = f"{eu.id:04d}"

        if codigo_nuevo in asignados:
            raise RuntimeError(
                f"Colisión al asignar codigo_nuevo='{codigo_nuevo}' para la "
                f"UnidadEjecutora id={eu.id} (nombre='{eu.nombre}'): ese código "
                f"ya fue asignado a la fila id={asignados[codigo_nuevo]}. "
                "Corrija los datos antes de aplicar la migración."
            )
        asignados[codigo_nuevo] = eu.id
        eu.codigo_nuevo = codigo_nuevo
        eu.save(update_fields=["codigo_nuevo"])

    # Verificación final de unicidad.
    count_total = ExecutingUnit.objects.count()
    if len(asignados) != count_total:
        raise RuntimeError(
            f"La verificación de unicidad de codigo_nuevo falló: se procesaron "
            f"{len(asignados)} códigos únicos pero la tabla tiene {count_total} filas."
        )


def poblar_ipress_codigo(apps, schema_editor):
    """Backfill de unidad_ejecutora_codigo en Ipress.

    Para cada Ipress con unidad_ejecutora_id no nulo, copia el codigo_nuevo
    del ExecutingUnit correspondiente.
    """
    Ipress = apps.get_model("convenios", "Ipress")
    ExecutingUnit = apps.get_model("convenios", "ExecutingUnit")

    # Cache de id -> codigo_nuevo para evitar consultas repetidas.
    eu_por_id = {eu.id: eu.codigo_nuevo for eu in ExecutingUnit.objects.all()}

    for ipress in Ipress.objects.filter(unidad_ejecutora_id__isnull=False):
        ue_id = ipress.unidad_ejecutora_id
        codigo_nuevo = eu_por_id.get(ue_id)
        if codigo_nuevo is None:
            raise RuntimeError(
                f"Integridad referencial rota: la Ipress id={ipress.id} "
                f"(codigo_renipress='{ipress.codigo_renipress}') referencia "
                f"unidad_ejecutora_id={ue_id} que no existe en la tabla "
                "`unidad_ejecutora`. Corrija los datos antes de aplicar la migración."
            )
        ipress.unidad_ejecutora_codigo = codigo_nuevo
        ipress.save(update_fields=["unidad_ejecutora_codigo"])


def poblar_convenio_codigo(apps, schema_editor):
    """Backfill de unidad_ejecutora_codigo en Convention.

    Para cada Convention con unidad_ejecutora_id no nulo, copia el codigo_nuevo.
    Si es nulo, deja unidad_ejecutora_codigo como None.
    """
    Convention = apps.get_model("convenios", "Convention")
    ExecutingUnit = apps.get_model("convenios", "ExecutingUnit")

    eu_por_id = {eu.id: eu.codigo_nuevo for eu in ExecutingUnit.objects.all()}

    for conv in Convention.objects.filter(unidad_ejecutora_id__isnull=False):
        ue_id = conv.unidad_ejecutora_id
        codigo_nuevo = eu_por_id.get(ue_id)
        if codigo_nuevo is None:
            raise RuntimeError(
                f"Integridad referencial rota: el Convenio id={conv.id} "
                f"referencia unidad_ejecutora_id={ue_id} que no existe en la "
                "tabla `unidad_ejecutora`. Corrija los datos antes de aplicar la migración."
            )
        conv.unidad_ejecutora_codigo = codigo_nuevo
        conv.save(update_fields=["unidad_ejecutora_codigo"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0043_healthgeographicscope_gobierno_regional"),
    ]

    operations = [
        # Paso 1: campo transitorio en ExecutingUnit.
        migrations.AddField(
            model_name="executingunit",
            name="codigo_nuevo",
            field=models.CharField(
                max_length=4,
                null=True,
                blank=True,
                db_column="codigo_nuevo",
                help_text="Campo transitorio: código presupuestal de 4 dígitos (futura PK)",
            ),
        ),
        # Paso 2: backfill de codigo_nuevo.
        migrations.RunPython(poblar_codigo_nuevo, reverse_code=migrations.RunPython.noop),
        # Paso 3: columna transitoria en Ipress (db_column distinto para no colisionar
        # con la columna FK existente unidad_ejecutora_id).
        migrations.AddField(
            model_name="ipress",
            name="unidad_ejecutora_codigo",
            field=models.CharField(
                max_length=4,
                null=True,
                blank=True,
                db_column="unidad_ejecutora_codigo_nuevo",
                help_text=(
                    "Campo transitorio: código de la unidad ejecutora (futura FK textual)"
                ),
            ),
        ),
        # Paso 4: backfill de ipress.unidad_ejecutora_codigo.
        migrations.RunPython(poblar_ipress_codigo, reverse_code=migrations.RunPython.noop),
        # Paso 5: columna transitoria en Convention (db_column distinto).
        migrations.AddField(
            model_name="convention",
            name="unidad_ejecutora_codigo",
            field=models.CharField(
                max_length=4,
                null=True,
                blank=True,
                db_column="convenio_unidad_ejecutora_codigo_nuevo",
                help_text=(
                    "Campo transitorio: código de la unidad ejecutora (futura FK textual)"
                ),
            ),
        ),
        # Paso 6: backfill de convention.unidad_ejecutora_codigo.
        migrations.RunPython(poblar_convenio_codigo, reverse_code=migrations.RunPython.noop),
    ]
