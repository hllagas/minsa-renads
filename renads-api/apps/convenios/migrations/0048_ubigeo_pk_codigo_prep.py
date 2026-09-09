"""Refactor de la PK de ``Ubigeo`` — preparación: columnas transitorias + backfill (convenios).

Añade la columna transitoria ``ubigeo_codigo`` (varchar 6, null) a los 5 modelos de
convenios que referencian ``Ubigeo`` por FK entera, y la rellena con el ``codigo``
correspondiente del ubigeo actual.

Las columnas enteras ``ubigeo_id`` se eliminan en ``0048b``; la PK se promueve en ``0049``.
"""

from django.db import migrations, models


def backfill_ubigeo_codigos(apps, schema_editor):
    Ubigeo = apps.get_model("convenios", "Ubigeo")
    codigos = {u.id: u.codigo for u in Ubigeo.objects.all()}

    for model_name in ["RegionalGovernment", "Ipress", "University", "Faculty", "UniversityCampus"]:
        Model = apps.get_model("convenios", model_name)
        filas = list(Model.objects.filter(ubigeo_id__isnull=False))
        for obj in filas:
            obj.ubigeo_codigo = codigos.get(obj.ubigeo_id)
        if filas:
            Model.objects.bulk_update(filas, ["ubigeo_codigo"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0047_ipress_pk_renipress_promote"),
    ]

    operations = [
        migrations.AddField(
            model_name="regionalgovernment",
            name="ubigeo_codigo",
            field=models.CharField(
                max_length=6, null=True, blank=True,
                db_column="ubigeo_codigo",
                help_text="Campo transitorio: código UBIGEO (varchar 6)",
            ),
        ),
        migrations.AddField(
            model_name="ipress",
            name="ubigeo_codigo",
            field=models.CharField(
                max_length=6, null=True, blank=True,
                db_column="ubigeo_codigo",
                help_text="Campo transitorio: código UBIGEO (varchar 6)",
            ),
        ),
        migrations.AddField(
            model_name="university",
            name="ubigeo_codigo",
            field=models.CharField(
                max_length=6, null=True, blank=True,
                db_column="ubigeo_codigo",
                help_text="Campo transitorio: código UBIGEO (varchar 6)",
            ),
        ),
        migrations.AddField(
            model_name="faculty",
            name="ubigeo_codigo",
            field=models.CharField(
                max_length=6, null=True, blank=True,
                db_column="ubigeo_codigo",
                help_text="Campo transitorio: código UBIGEO (varchar 6)",
            ),
        ),
        migrations.AddField(
            model_name="universitycampus",
            name="ubigeo_codigo",
            field=models.CharField(
                max_length=6, null=True, blank=True,
                db_column="ubigeo_codigo",
                help_text="Campo transitorio: código UBIGEO (varchar 6)",
            ),
        ),
        migrations.RunPython(backfill_ubigeo_codigos, migrations.RunPython.noop),
    ]
