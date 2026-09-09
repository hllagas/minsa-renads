"""Renombra la tabla ``categoria`` a ``tipo_categoria``.

Corresponde al cambio ``Category.Meta.db_table = "tipo_categoria"`` en el modelo.
El FK ``ipress.categoria_id`` sigue referenciando la misma tabla (ahora ``tipo_categoria``);
SQLite 3.26+ actualiza automáticamente las referencias al renombrar.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0049_ubigeo_pk_codigo_promote"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="category",
            table="tipo_categoria",
        ),
    ]
