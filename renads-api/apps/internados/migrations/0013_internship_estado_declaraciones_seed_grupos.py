"""F3: estado de declaraciones juradas del interno + seed de grupos (Universidad, Interno).

- ``AddField`` ``Internship.estado_declaraciones`` (default ``PENDIENTE`` — RN-23).
- ``RunPython`` idempotente que crea los grupos ``Universidad`` e ``Interno`` (RN-20/22).
"""

from django.db import migrations, models


GRUPOS = ["Universidad", "Interno"]


def crear_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nombre in GRUPOS:
        Group.objects.get_or_create(name=nombre)


def eliminar_grupos(apps, schema_editor):
    # No-op: no se eliminan grupos en el rollback para no romper perfiles existentes.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0012_annexdocument_help_text"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="internship",
            name="estado_declaraciones",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("COMPLETAS", "Completas"),
                    ("OBSERVADAS", "Observadas"),
                    ("VALIDADAS", "Validadas"),
                ],
                default="PENDIENTE",
                help_text="Estado de las declaraciones juradas del interno (RN-23)",
                max_length=20,
                verbose_name="estado de declaraciones juradas",
            ),
        ),
        migrations.RunPython(crear_grupos, eliminar_grupos),
    ]
