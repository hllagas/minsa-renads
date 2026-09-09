"""Refactor de la PK de ``Ipress`` — paso intermedio (internados): eliminar las FK enteras.

Elimina las columnas FK enteras de ``Ipress`` de los modelos internados
(``Internship.ipress``, ``Rotation.ipress_origen``, ``Rotation.ipress_destino``,
``Tutor.ipress``) ANTES de que ``convenios/0047`` promueva ``codigo_renipress`` a PK
y elimine la columna ``id``.

Sin este paso, el ``check_constraints()`` que Django 6 llama siempre al salir del
``SchemaEditor`` detectaría que las FK enteras referencian ``ipress(id)`` — columna
que ya no existe tras 0047 — y produciría ``foreign key mismatch``.

Tras este paso los 4 modelos de internados NO tienen FK a ``Ipress``; la FK varchar
se restituye en ``0022_ipress_fk_renipress`` una vez que ``convenios/0047`` ha
promovido el PK.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0021_ipress_codigo_transitorio"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="internship",
            name="ipress",
        ),
        migrations.RemoveField(
            model_name="rotation",
            name="ipress_origen",
        ),
        migrations.RemoveField(
            model_name="rotation",
            name="ipress_destino",
        ),
        migrations.RemoveField(
            model_name="tutor",
            name="ipress",
        ),
    ]
