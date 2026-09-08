"""Refactor: traslada `gobierno_regional` de `organo_directorio` a `convenio`.

Se agrega el FK `convenio.gobierno_regional` (nullable, PROTECT), se copia el GORE
existente de cada `organo_directorio` a los convenios que lo referencian (RN-GORE-6),
se colapsa la unicidad de `organo_directorio` a `(organo, nombre)` y finalmente se
elimina la columna `organo_directorio.gobierno_regional_id`.

Orden estricto: AddField → RunPython (copia del GORE) → RemoveConstraint x2 →
AddConstraint → RemoveField.
"""

import django.db.models.deletion
from django.db import migrations, models


def copiar_gore_a_convenio(apps, schema_editor):
    """Copia `organo_directorio.gobierno_regional_id` → `convenio.gobierno_regional_id`.

    Se ejecuta ANTES de borrar la columna origen. Para cada convenio cuyo órgano del
    directorio tenga un GORE asignado, se traslada ese GORE al propio convenio.

    Nota de verificación al momento del refactor: existían 3 órganos del directorio con
    `gobierno_regional_id` no nulo y 0 convenios que los referenciaran, por lo que en la
    práctica no había filas de `convenio` que actualizar. El paso se mantiene real (no
    `noop`) para no perder el dato si se corre sobre una base con convenios regionales.
    """
    Convention = apps.get_model("convenios", "Convention")
    convenios = list(
        Convention.objects.select_related("organo_directorio").filter(
            organo_directorio__gobierno_regional__isnull=False
        )
    )
    for convenio in convenios:
        convenio.gobierno_regional_id = convenio.organo_directorio.gobierno_regional_id
    if convenios:
        Convention.objects.bulk_update(convenios, ["gobierno_regional"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0040_alter_executingunit_tipo_organo_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="convention",
            name="gobierno_regional",
            field=models.ForeignKey(
                blank=True,
                db_column="gobierno_regional_id",
                help_text="Gobierno Regional del convenio (solo Convenio Marco regional).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="convenios",
                to="convenios.regionalgovernment",
            ),
        ),
        # RN-GORE-6: copiar el GORE del órgano al convenio antes de borrar la columna
        # origen. Irreversible (la columna origen se elimina en el paso final).
        migrations.RunPython(
            copiar_gore_a_convenio, reverse_code=migrations.RunPython.noop
        ),
        migrations.RemoveConstraint(
            model_name="organdirectory",
            name="uniq_organo_dir_organo_gore_nombre",
        ),
        migrations.RemoveConstraint(
            model_name="organdirectory",
            name="uniq_organo_dir_organo_nombre_sin_gore",
        ),
        migrations.AddConstraint(
            model_name="organdirectory",
            constraint=models.UniqueConstraint(
                fields=("organo", "nombre"),
                name="uniq_organo_dir_organo_nombre",
            ),
        ),
        migrations.RemoveField(
            model_name="organdirectory",
            name="gobierno_regional",
        ),
    ]
