"""Refactor de la PK de ``Ubigeo`` — paso intermedio: eliminar las FK enteras (internados).

Elimina las columnas ``ubigeo_id`` (integer FK) de ``Student`` y ``Tutor`` ANTES de
que ``convenios/0049`` promueva ``ubigeo.codigo`` a PK y elimine ``ubigeo.id``.

La FK varchar se restituye en ``0024`` desde las columnas transitorias ``ubigeo_codigo``.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0023_ubigeo_codigo_transitorio"),
    ]

    operations = [
        migrations.RemoveField(model_name="student", name="ubigeo"),
        migrations.RemoveField(model_name="tutor", name="ubigeo"),
    ]
