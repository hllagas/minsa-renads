"""Seed de catálogos cerrados del Módulo 3 (Registrar Actividades)."""

from django.db import migrations


# (código, nombre, orden)
ACTIVITY_STATUSES = [
    ("REGISTRADA", "Registrada", 1),
    ("PENDIENTE_VALIDACION", "Pendiente de validación", 2),
    ("OBSERVADA", "Observada", 3),
    ("SUBSANADA", "Subsanada", 4),
    ("VALIDADA", "Validada", 5),
    ("RECHAZADA", "Rechazada", 6),
    ("CERRADA", "Cerrada", 7),
]


def seed(apps, schema_editor):
    ActivityStatus = apps.get_model("actividades", "ActivityStatus")
    for codigo, nombre, orden in ACTIVITY_STATUSES:
        ActivityStatus.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "orden": orden}
        )


def unseed(apps, schema_editor):
    ActivityStatus = apps.get_model("actividades", "ActivityStatus")
    ActivityStatus.objects.filter(codigo__in=[r[0] for r in ACTIVITY_STATUSES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("actividades", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
