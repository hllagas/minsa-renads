"""Seed de roles institucionales (auth.Group) de RENADS.

Roles derivados de los actores del proyecto (ver docs de módulos). Los permisos
finos se asignan posteriormente; aquí solo se crean los grupos.
"""

from django.db import migrations


ROLES = [
    "Administrador RENADS",
    "DIGEP",
    "CONAPRES",
    "OGAJ",
    "Secretaría General",
    "Despacho VICEPAS",
    "Gobierno Regional",
    "Universidad",
    "Sede docente",
    "Autoridad de convenio",
    "Tutor",
    "Auditor",
]


def seed(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nombre in ROLES:
        Group.objects.get_or_create(name=nombre)


def unseed(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0003_seed_especialidad_ambito"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
