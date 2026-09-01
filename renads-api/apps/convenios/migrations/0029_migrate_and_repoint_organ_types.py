"""Refactor de entidades (2/3): migración de datos + reapuntado de FKs.

Migra las filas de `tipo_organo` a `organo_directorio` (una fila de directorio por
cada tipo de órgano), rellena `organo_directorio.categoria`, y reapunta las FKs
`unidad_ejecutora.tipo_organo_id` y `universidad.tipo_entidad_id` desde `tipo_organo`
hacia las nuevas filas de `organo_directorio`.

Circularidad constraint↔valores (portátil SQLite + PostgreSQL — bridge sin constraint):
- No se pueden escribir ids de `organo_directorio` en las columnas mientras la
  constraint de BD apunta a `tipo_organo`; ni reapuntar la constraint mientras las
  columnas guardan ids viejos de `tipo_organo`. En SQLite el chequeo de FK está
  desactivado durante la transacción atómica, pero en PostgreSQL las FKs son
  `NOT DEFERRABLE INITIALLY IMMEDIATE` y se validan en cada `UPDATE` → abortarían.
- Solución portátil, en tres pasos dentro de la misma migración:
  1. `AlterField` (db_constraint=False) de ambas FKs → apunta el state a
     `organo_directorio` y, en Postgres, DROPa la constraint vieja hacia `tipo_organo`
     SIN crear una nueva. La columna queda como entero sin FK: no hay validación,
     así que reescribir valores no falla aunque aún sean ids de `tipo_organo`.
  2. `RunPython` crea el directorio desde `tipo_organo` y reescribe los valores de
     las 2 columnas al nuevo id de `organo_directorio` (sin constraint viva).
  3. `AlterField` (db_constraint=True) de ambas FKs → estado final; en Postgres
     AGREGA la constraint hacia `organo_directorio`. Como los valores ya fueron
     reescritos, la validación de la constraint pasa. En SQLite reconstruye la tabla
     y el `foreign_key_check` de cierre valida el estado final coherente.

El backfill regional deriva la categoría del `tipo_organo.codigo`: GERESA/DIRESA →
GOBIERNO_REGIONAL, DIRIS → MINSA_DIRIS. El resto por `organo.nombre`.
"""

from django.db import migrations, models
import django.db.models.deletion


# Mapa nombre canónico de `organo` → categoría del directorio.
ORGAN_NAME_TO_CATEGORY = {
    "Órgano del MINSA": "ORGANO_MINSA",
    "MINSA Central": "ORGANO_MINSA",  # nombre heredado en algunas BD
    "Universidad": "UNIVERSIDAD",
    "Órgano Regional": "GOBIERNO_REGIONAL",  # fallback si la BD no fue renombrada
    "Gobierno Regional": "GOBIERNO_REGIONAL",
    "MINSA DIRIS": "MINSA_DIRIS",
    "Unidad Ejecutora": "UNIDAD_EJECUTORA",
}

# Códigos regionales de `tipo_organo` → categoría (prioritario sobre el nombre de organo).
REGIONAL_CODE_TO_CATEGORY = {
    "GERESA": "GOBIERNO_REGIONAL",
    "DIRESA": "GOBIERNO_REGIONAL",
    "DIRIS": "MINSA_DIRIS",
}

# Nombres canónicos que deben existir en `organo` (labels de las 5 categorías).
CANONICAL_ORGAN_NAMES = [
    "Órgano del MINSA",
    "Universidad",
    "Gobierno Regional",
    "MINSA DIRIS",
    "Unidad Ejecutora",
]


def _categoria_de(organo_nombre, tipo_codigo):
    """Deriva la categoría del directorio para un par (organo, tipo_organo.codigo)."""
    if organo_nombre in {"Órgano Regional", "Gobierno Regional"} and tipo_codigo:
        cat = REGIONAL_CODE_TO_CATEGORY.get(tipo_codigo)
        if cat:
            return cat
    cat = ORGAN_NAME_TO_CATEGORY.get(organo_nombre)
    if cat is None:
        raise ValueError(
            f"No se pudo derivar la categoría del directorio para organo='{organo_nombre}' "
            f"(tipo_organo.codigo='{tipo_codigo}'). Revise el seed de `organo`."
        )
    return cat


def forwards(apps, schema_editor):
    Organ = apps.get_model("convenios", "Organ")
    OrganType = apps.get_model("convenios", "OrganType")
    OrganDirectory = apps.get_model("convenios", "OrganDirectory")
    ExecutingUnit = apps.get_model("convenios", "ExecutingUnit")
    University = apps.get_model("convenios", "University")

    # --- 1. Normaliza los nombres de `organo` a los labels canónicos de categoría. ---
    renombres = {"Órgano Regional": "Gobierno Regional", "MINSA Central": "Órgano del MINSA"}
    for viejo, nuevo in renombres.items():
        Organ.objects.filter(nombre=viejo).update(nombre=nuevo)
    for nombre in CANONICAL_ORGAN_NAMES:
        Organ.objects.get_or_create(nombre=nombre, defaults={"estado": True})

    # --- 2. Backfill de `organo_directorio.categoria` desde organo + tipo_organo. ---
    for od in OrganDirectory.objects.select_related("organo", "tipo_organo").all():
        organo_nombre = od.organo.nombre if od.organo_id else ""
        tipo_codigo = od.tipo_organo.codigo if od.tipo_organo_id else ""
        od.categoria = _categoria_de(organo_nombre, tipo_codigo)
        od.save(update_fields=["categoria"])

    # --- 3. Crea una fila de `organo_directorio` por cada `tipo_organo`. ---
    # En este punto la columna `organo_directorio.organo_id` sigue siendo NOT NULL
    # (se elimina en 0030), por lo que se asigna el `organo` de la categoría (por label).
    CATEGORY_TO_ORGAN_NAME = {
        "ORGANO_MINSA": "Órgano del MINSA",
        "UNIVERSIDAD": "Universidad",
        "GOBIERNO_REGIONAL": "Gobierno Regional",
        "MINSA_DIRIS": "MINSA DIRIS",
        "UNIDAD_EJECUTORA": "Unidad Ejecutora",
    }
    organos_por_nombre = {o.nombre: o for o in Organ.objects.all()}

    mapeo = {}  # {tipo_organo.id → nuevo organo_directorio.id}
    for ot in OrganType.objects.select_related("organo").all():
        categoria = _categoria_de(ot.organo.nombre, ot.codigo)
        organo = organos_por_nombre[CATEGORY_TO_ORGAN_NAME[categoria]]
        nuevo = OrganDirectory.objects.create(
            organo=organo,
            categoria=categoria,
            gobierno_regional=None,
            nombre=ot.nombre,
            siglas=ot.codigo or "",
            activo=ot.activo,
        )
        mapeo[ot.id] = nuevo.id

    # --- 4. Reapunta los VALORES de las FKs a los nuevos ids de directorio. ---
    # Este RunPython corre DESPUÉS del AlterField(db_constraint=False) de ambas FKs:
    # en Postgres ya no existe la constraint vieja hacia `tipo_organo` (fue DROPada) y
    # aún no se creó la nueva, de modo que reescribir ids de `organo_directorio` en las
    # columnas no dispara ninguna validación. En SQLite el chequeo de FK está
    # desactivado durante la transacción atómica. El AlterField(db_constraint=True)
    # posterior agrega/reconstruye la constraint hacia `organo_directorio`, que valida
    # los valores ya reescritos.
    for eu in ExecutingUnit.objects.all():
        if eu.tipo_organo_id in mapeo:
            ExecutingUnit.objects.filter(pk=eu.pk).update(
                tipo_organo_id=mapeo[eu.tipo_organo_id]
            )
    for uni in University.objects.all():
        if uni.tipo_entidad_id in mapeo:
            University.objects.filter(pk=uni.pk).update(
                tipo_entidad_id=mapeo[uni.tipo_entidad_id]
            )

    # --- 5. Coherencia de cargos DIRIS (observación BAJA). ---
    # NOTA para migración a producción: los `cargo_ejecutivo`/`organo_representante`
    # de directorios DIRIS deberían colgar del `organo` "MINSA DIRIS" (coherente con
    # OrganRepresentativeSerializer). El reapuntado anterior solo toca las columnas de
    # `unidad_ejecutora`/`universidad`, no los cargos. No se fuerza aquí porque el
    # modelo histórico de `organo` de cargos/representantes puede variar entre BDs;
    # revisar y corregir manualmente los cargos DIRIS antes de migrar prod.


def noop(apps, schema_editor):
    """Refactor no reversible a nivel de datos (los `tipo_organo` ya no existen)."""


# --- Campos puente (paso 1): apuntan a organo_directorio SIN constraint de BD. ---
# En Postgres, el AlterField desde el FK viejo (→ tipo_organo) hacia estos DROPa la
# constraint vieja y NO agrega una nueva (db_constraint=False). La columna queda como
# entero suelto: el RunPython puede reescribir valores sin disparar validación de FK.
_EU_TIPO_ORGANO_BRIDGE = models.ForeignKey(
    to="convenios.organdirectory",
    on_delete=django.db.models.deletion.PROTECT,
    db_column="tipo_organo_id",
    db_constraint=False,
    related_name="+",
    limit_choices_to={"categoria": "UNIDAD_EJECUTORA"},
    help_text="Tipo de unidad ejecutora del directorio (categoría UNIDAD_EJECUTORA)",
)
_UNI_TIPO_ENTIDAD_BRIDGE = models.ForeignKey(
    to="convenios.organdirectory",
    on_delete=django.db.models.deletion.PROTECT,
    db_column="tipo_entidad_id",
    db_constraint=False,
    limit_choices_to={"categoria": "UNIVERSIDAD"},
    help_text="Tipo de entidad del directorio (categoría UNIVERSIDAD)",
)

# --- Campos destino final (paso 3): FKs con constraint hacia organo_directorio. ---
# En Postgres, el AlterField desde el puente (db_constraint=False) hacia estos AGREGA
# la constraint hacia organo_directorio; los valores ya fueron reescritos → valida OK.
_EU_TIPO_ORGANO = models.ForeignKey(
    to="convenios.organdirectory",
    on_delete=django.db.models.deletion.PROTECT,
    db_column="tipo_organo_id",
    related_name="+",
    limit_choices_to={"categoria": "UNIDAD_EJECUTORA"},
    help_text="Tipo de unidad ejecutora del directorio (categoría UNIDAD_EJECUTORA)",
)
_UNI_TIPO_ENTIDAD = models.ForeignKey(
    to="convenios.organdirectory",
    on_delete=django.db.models.deletion.PROTECT,
    db_column="tipo_entidad_id",
    limit_choices_to={"categoria": "UNIVERSIDAD"},
    help_text="Tipo de entidad del directorio (categoría UNIVERSIDAD)",
)


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0028_refactor_entities_schema_prep"),
    ]

    operations = [
        # (1) AlterField (db_constraint=False): apunta el state a organo_directorio y, en
        #     Postgres, DROPa la constraint vieja hacia tipo_organo sin crear una nueva.
        #     La columna queda sin FK viva → el RunPython siguiente puede reescribir ids.
        migrations.AlterField(
            model_name="executingunit", name="tipo_organo", field=_EU_TIPO_ORGANO_BRIDGE,
        ),
        migrations.AlterField(
            model_name="university", name="tipo_entidad", field=_UNI_TIPO_ENTIDAD_BRIDGE,
        ),
        # (2) Datos: seed/backfill, crear directorio desde tipo_organo y reapuntar valores.
        #     Corre sin constraint FK viva sobre las columnas → portátil en Postgres.
        migrations.RunPython(forwards, noop),
        # (3) AlterField (db_constraint=True): estado final. En Postgres AGREGA la
        #     constraint hacia organo_directorio, que valida los valores ya reescritos.
        migrations.AlterField(
            model_name="executingunit", name="tipo_organo", field=_EU_TIPO_ORGANO,
        ),
        migrations.AlterField(
            model_name="university", name="tipo_entidad", field=_UNI_TIPO_ENTIDAD,
        ),
    ]
