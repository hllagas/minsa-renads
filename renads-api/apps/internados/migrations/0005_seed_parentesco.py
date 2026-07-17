"""Seed del catálogo `parentesco` (tipos de parentesco del contacto de emergencia)."""

from django.db import migrations


# (código, nombre)
RELATIONSHIP_TYPES = [
    ("PADRE", "Padre"),
    ("MADRE", "Madre"),
    ("HERMANO", "Hermano/a"),
    ("CONYUGE", "Cónyuge"),
    ("HIJO", "Hijo/a"),
    ("ABUELO", "Abuelo/a"),
    ("TIO", "Tío/a"),
    ("OTRO", "Otro"),
]


def seed(apps, schema_editor):
    RelationshipType = apps.get_model("internados", "RelationshipType")
    for codigo, nombre in RELATIONSHIP_TYPES:
        RelationshipType.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})


def unseed(apps, schema_editor):
    RelationshipType = apps.get_model("internados", "RelationshipType")
    RelationshipType.objects.filter(codigo__in=[r[0] for r in RELATIONSHIP_TYPES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0004_rename_student_add_fields"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
