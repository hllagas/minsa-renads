"""Refactor de la PK de ``Ubigeo`` — paso intermedio: eliminar las FK enteras (convenios).

Elimina las columnas ``ubigeo_id`` (integer FK) de los 5 modelos de convenios ANTES de
que ``0049`` promueva ``ubigeo.codigo`` a PK y elimine ``ubigeo.id``.

Sin este paso, ``check_constraints()`` de Django 6 detectaría que las FK enteras
referencian ``ubigeo(id)`` — columna que ya no existe tras la promoción — y produciría
``foreign key mismatch``.

La FK varchar se restituye en ``0049`` desde las columnas transitorias ``ubigeo_codigo``.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0048_ubigeo_pk_codigo_prep"),
    ]

    operations = [
        migrations.RemoveField(model_name="regionalgovernment", name="ubigeo"),
        migrations.RemoveField(model_name="ipress", name="ubigeo"),
        migrations.RemoveField(model_name="university", name="ubigeo"),
        migrations.RemoveField(model_name="faculty", name="ubigeo"),
        migrations.RemoveField(model_name="universitycampus", name="ubigeo"),
    ]
