# Hand-written: OrganDirectory.categoria (CharField) → FK organo (→ Organ) + nueva unicidad.
#
# Orden: 1) add organo nullable; 2) data migration (categoria→Organ por nombre) +
# verificación de colisiones; 3) organo NOT NULL; 4) drop categoria; 5) swap constraints
# (quita uniq_organo_directorio_por_gore de 0037, agrega las 2 nuevas por
# (organo, gobierno_regional, nombre) con/ sin GORE).
#
# reverse_code repuebla categoria desde organo.nombre (mapa inverso). Reversibilidad
# best-effort (re-crear la columna categoria NOT NULL en reverse es limitado).

import django.db.models.deletion
from django.db import migrations, models

# categoria code → Organ.nombre (los nombres NO coinciden con los labels de categoría;
# el mapeo es por nombre, NO por id, para no depender de la BD).
CODE_A_ORGANO_NOMBRE = {
    "ORGANO_MINSA": "MINSA Administrativo",
    "UNIVERSIDAD": "Universidad",
    "GOBIERNO_REGIONAL": "Gobierno Regional",
    "UNIDAD_EJECUTORA": "Unidad Ejecutora",
    "MINSA_DIRIS": "MINSA DIRIS",
}
NOMBRE_A_CODE = {v: k for k, v in CODE_A_ORGANO_NOMBRE.items()}


def poblar_organo(apps, schema_editor):
    OrganDirectory = apps.get_model("convenios", "OrganDirectory")
    Organ = apps.get_model("convenios", "Organ")

    # Cache Organ por nombre.
    organos = {o.nombre: o for o in Organ.objects.all()}
    for code, nombre in CODE_A_ORGANO_NOMBRE.items():
        if nombre not in organos:
            raise RuntimeError(
                f"No existe la fila Organ con nombre '{nombre}' (para categoria "
                f"'{code}'). Cargue la tabla `organo` antes de migrar."
            )

    for od in OrganDirectory.objects.all():
        nombre_organo = CODE_A_ORGANO_NOMBRE.get(od.categoria)
        if nombre_organo is None:
            raise RuntimeError(
                f"OrganDirectory id={od.pk} tiene categoria '{od.categoria}' sin "
                f"mapeo a Organ. Revise los datos antes de migrar."
            )
        od.organo = organos[nombre_organo]
        od.save(update_fields=["organo"])

    # Verificación de colisiones ANTES de crear las constraints de unicidad.
    from collections import Counter
    con_gore = Counter()
    sin_gore = Counter()
    for od in OrganDirectory.objects.all():
        if od.gobierno_regional_id is not None:
            con_gore[(od.organo_id, od.gobierno_regional_id, od.nombre)] += 1
        else:
            sin_gore[(od.organo_id, od.nombre)] += 1
    colisiones = [k for k, n in con_gore.items() if n > 1] + [
        k for k, n in sin_gore.items() if n > 1
    ]
    if colisiones:
        raise RuntimeError(
            "Colisiones de unicidad (organo, gobierno_regional, nombre) detectadas: "
            f"{colisiones}. Limpie los duplicados antes de aplicar la migración."
        )


def revertir_organo(apps, schema_editor):
    OrganDirectory = apps.get_model("convenios", "OrganDirectory")
    for od in OrganDirectory.objects.select_related("organo").all():
        code = NOMBRE_A_CODE.get(getattr(od.organo, "nombre", None))
        if code:
            od.categoria = code
            od.save(update_fields=["categoria"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0038_organrepresentative_polimorfico"),
    ]

    operations = [
        # 1) organo nullable temporal.
        migrations.AddField(
            model_name="organdirectory",
            name="organo",
            field=models.ForeignKey(
                null=True, db_column="organo_id",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="organos_directorio_por_categoria",
                to="convenios.organ",
                help_text="Categoría del órgano (FK a la tabla canónica `organo`)",
            ),
        ),
        # 2) data migration + verificación de colisiones.
        migrations.RunPython(poblar_organo, revertir_organo),
        # 3) organo NOT NULL.
        migrations.AlterField(
            model_name="organdirectory",
            name="organo",
            field=models.ForeignKey(
                db_column="organo_id",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="organos_directorio_por_categoria",
                to="convenios.organ",
                help_text="Categoría del órgano (FK a la tabla canónica `organo`)",
            ),
        ),
        # 4) drop categoria.
        migrations.RemoveField(model_name="organdirectory", name="categoria"),
        # 5) swap constraints.
        migrations.RemoveConstraint(
            model_name="organdirectory", name="uniq_organo_directorio_por_gore",
        ),
        migrations.AddConstraint(
            model_name="organdirectory",
            constraint=models.UniqueConstraint(
                condition=models.Q(("gobierno_regional__isnull", False)),
                fields=("organo", "gobierno_regional", "nombre"),
                name="uniq_organo_dir_organo_gore_nombre",
            ),
        ),
        migrations.AddConstraint(
            model_name="organdirectory",
            constraint=models.UniqueConstraint(
                condition=models.Q(("gobierno_regional__isnull", True)),
                fields=("organo", "nombre"),
                name="uniq_organo_dir_organo_nombre_sin_gore",
            ),
        ),
    ]
