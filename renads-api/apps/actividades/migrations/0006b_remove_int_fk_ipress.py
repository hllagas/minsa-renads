"""Refactor de la PK de ``Ipress`` — paso intermedio (actividades): eliminar la FK entera.

Elimina la columna FK entera de ``Ipress`` de ``TeachingActivity.ipress`` ANTES de que
``convenios/0047`` promueva ``codigo_renipress`` a PK y elimine la columna ``id``.

La FK varchar se restituye en ``0007_ipress_fk_renipress`` después de 0047.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0006_ipress_codigo_transitorio"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="teachingactivity",
            name="ipress",
        ),
    ]
