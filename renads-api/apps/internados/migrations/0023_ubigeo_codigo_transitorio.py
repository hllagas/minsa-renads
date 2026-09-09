"""Refactor de la PK de ``Ubigeo`` — preparación: columnas transitorias + backfill (internados).

Añade la columna transitoria ``ubigeo_codigo`` (varchar 6, null) a ``Student`` y ``Tutor``,
y la rellena con el ``codigo`` UBIGEO correspondiente.

Depende de ``convenios/0048`` para acceder a ``Ubigeo`` en el estado histórico.
Las columnas enteras ``ubigeo_id`` se eliminan en ``0023b``; los FK reales en ``0024``.
"""

from django.db import migrations, models


def backfill_ubigeo_codigos(apps, schema_editor):
    Ubigeo = apps.get_model("convenios", "Ubigeo")
    codigos = {u.id: u.codigo for u in Ubigeo.objects.all()}

    for model_name in ["Student", "Tutor"]:
        Model = apps.get_model("internados", model_name)
        filas = list(Model.objects.filter(ubigeo_id__isnull=False))
        for obj in filas:
            obj.ubigeo_codigo = codigos.get(obj.ubigeo_id)
        if filas:
            Model.objects.bulk_update(filas, ["ubigeo_codigo"])


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0022_ipress_fk_renipress"),
        ("convenios", "0048_ubigeo_pk_codigo_prep"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="ubigeo_codigo",
            field=models.CharField(
                max_length=6, null=True, blank=True,
                db_column="ubigeo_codigo",
                help_text="Campo transitorio: código UBIGEO (varchar 6)",
            ),
        ),
        migrations.AddField(
            model_name="tutor",
            name="ubigeo_codigo",
            field=models.CharField(
                max_length=6, null=True, blank=True,
                db_column="ubigeo_codigo",
                help_text="Campo transitorio: código UBIGEO (varchar 6)",
            ),
        ),
        migrations.RunPython(backfill_ubigeo_codigos, migrations.RunPython.noop),
    ]
