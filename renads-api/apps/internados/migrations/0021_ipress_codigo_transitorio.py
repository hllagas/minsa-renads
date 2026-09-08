"""Refactor de la PK de ``Ipress`` — parte B (internados): columnas transitorias + backfill.

Agrega las columnas transitorias ``ipress_codigo`` a las 4 FK de ``Ipress`` en internados
(``Internship.ipress``, ``Rotation.ipress_origen``, ``Rotation.ipress_destino``,
``Tutor.ipress``) y las rellena con el ``codigo_renipress`` correspondiente. Los nulos de
``Tutor.ipress`` (SET_NULL) quedan nulos.

En dev la tabla ``ipress`` está vacía, por lo que el backfill es noop efectivo (0 filas con
``ipress_id`` no nulo); queda correcto para producción.
"""

from django.db import migrations, models


def backfill_ipress_codigo_internados(apps, schema_editor):
    """Copia ``codigo_renipress`` desde el Ipress referenciado por cada FK entera no nula."""
    Internship = apps.get_model("internados", "Internship")
    Rotation = apps.get_model("internados", "Rotation")
    Tutor = apps.get_model("internados", "Tutor")
    Ipress = apps.get_model("convenios", "Ipress")

    codigo_por_id = {ip.id: ip.codigo_renipress for ip in Ipress.objects.all()}

    def _codigo(ipress_id, etiqueta, fila_id):
        codigo = codigo_por_id.get(ipress_id)
        if codigo is None:
            raise RuntimeError(
                f"Integridad referencial rota: la fila id={fila_id} de `{etiqueta}` "
                f"referencia ipress_id={ipress_id} que no existe en la tabla `ipress`. "
                "Corrija los datos antes de aplicar la migración."
            )
        return codigo

    for fila in Internship.objects.filter(ipress_id__isnull=False):
        fila.ipress_codigo = _codigo(fila.ipress_id, "interno", fila.id)
        fila.save(update_fields=["ipress_codigo"])

    for fila in Rotation.objects.all():
        campos = []
        if fila.ipress_origen_id is not None:
            fila.ipress_origen_codigo = _codigo(fila.ipress_origen_id, "rotacion", fila.id)
            campos.append("ipress_origen_codigo")
        if fila.ipress_destino_id is not None:
            fila.ipress_destino_codigo = _codigo(fila.ipress_destino_id, "rotacion", fila.id)
            campos.append("ipress_destino_codigo")
        if campos:
            fila.save(update_fields=campos)

    for fila in Tutor.objects.filter(ipress_id__isnull=False):
        fila.ipress_codigo = _codigo(fila.ipress_id, "tutor", fila.id)
        fila.save(update_fields=["ipress_codigo"])


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0020_seed_anexos_proyecto"),
        ("convenios", "0046_ipress_pk_renipress_prep"),
    ]

    operations = [
        migrations.AddField(
            model_name="internship",
            name="ipress_codigo",
            field=models.CharField(
                max_length=8,
                null=True,
                blank=True,
                db_column="ipress_codigo",
                help_text="Campo transitorio: código RENIPRESS de la sede (futura FK textual)",
            ),
        ),
        migrations.AddField(
            model_name="rotation",
            name="ipress_origen_codigo",
            field=models.CharField(
                max_length=8,
                null=True,
                blank=True,
                db_column="ipress_origen_codigo",
                help_text="Campo transitorio: código RENIPRESS de la sede de origen",
            ),
        ),
        migrations.AddField(
            model_name="rotation",
            name="ipress_destino_codigo",
            field=models.CharField(
                max_length=8,
                null=True,
                blank=True,
                db_column="ipress_destino_codigo",
                help_text="Campo transitorio: código RENIPRESS de la sede de destino",
            ),
        ),
        migrations.AddField(
            model_name="tutor",
            name="ipress_codigo",
            field=models.CharField(
                max_length=8,
                null=True,
                blank=True,
                db_column="tutor_ipress_codigo",
                help_text="Campo transitorio: código RENIPRESS de la sede (futura FK textual)",
            ),
        ),
        migrations.RunPython(
            backfill_ipress_codigo_internados, reverse_code=migrations.RunPython.noop
        ),
    ]
