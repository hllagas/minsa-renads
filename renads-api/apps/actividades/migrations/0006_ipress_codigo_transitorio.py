"""Refactor de la PK de ``Ipress`` — parte B (actividades): columna transitoria + backfill.

Agrega la columna transitoria ``ipress_codigo`` a ``TeachingActivity.ipress`` y la rellena
con el ``codigo_renipress`` correspondiente. En dev la tabla ``ipress`` está vacía, por lo
que el backfill es noop efectivo; queda correcto para producción.
"""

from django.db import migrations, models


def backfill_ipress_codigo_actividades(apps, schema_editor):
    """Copia ``codigo_renipress`` desde el Ipress referenciado por ``TeachingActivity.ipress``."""
    TeachingActivity = apps.get_model("actividades", "TeachingActivity")
    Ipress = apps.get_model("convenios", "Ipress")

    codigo_por_id = {ip.id: ip.codigo_renipress for ip in Ipress.objects.all()}

    for fila in TeachingActivity.objects.filter(ipress_id__isnull=False):
        codigo = codigo_por_id.get(fila.ipress_id)
        if codigo is None:
            raise RuntimeError(
                f"Integridad referencial rota: la fila id={fila.id} de `actividad` "
                f"referencia ipress_id={fila.ipress_id} que no existe en la tabla "
                "`ipress`. Corrija los datos antes de aplicar la migración."
            )
        fila.ipress_codigo = codigo
        fila.save(update_fields=["ipress_codigo"])


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0005_rename_teachingactivity_interno"),
        ("convenios", "0046_ipress_pk_renipress_prep"),
    ]

    operations = [
        migrations.AddField(
            model_name="teachingactivity",
            name="ipress_codigo",
            field=models.CharField(
                max_length=8,
                null=True,
                blank=True,
                db_column="ipress_codigo",
                help_text="Campo transitorio: código RENIPRESS de la sede (futura FK textual)",
            ),
        ),
        migrations.RunPython(
            backfill_ipress_codigo_actividades, reverse_code=migrations.RunPython.noop
        ),
    ]
