"""Seed de catálogos cerrados del Módulo 2 (Registrar Internados)."""

from django.db import migrations


# (código, nombre, orden)
INTERNSHIP_STATUSES = [
    ("REGISTRADO", "Registrado", 1),
    ("PENDIENTE_VALIDACION", "Pendiente de validación", 2),
    ("OBSERVADO", "Observado", 3),
    ("VALIDADO", "Validado", 4),
    ("ACTIVO", "Activo", 5),
    ("EN_ROTACION_SOLICITADA", "En rotación solicitada", 6),
    ("EN_ROTACION_AUTORIZADA", "En rotación autorizada", 7),
    ("EN_ROTACION_OBSERVADA", "En rotación observada", 8),
    ("SUSPENDIDO", "Suspendido", 9),
    ("RETIRADO", "Retirado", 10),
    ("CULMINADO", "Culminado", 11),
    ("ANULADO", "Anulado", 12),
]

ROTATION_STATUSES = [
    ("SOLICITADA", "Solicitada", 1),
    ("PENDIENTE_AUTORIZACION", "Pendiente de autorización", 2),
    ("OBSERVADA", "Observada", 3),
    ("AUTORIZADA", "Autorizada", 4),
    ("RECHAZADA", "Rechazada", 5),
    ("EN_CURSO", "En curso", 6),
    ("CULMINADA", "Culminada", 7),
    ("CANCELADA", "Cancelada", 8),
]

IDENTITY_DOCUMENT_TYPES = [
    ("DNI", "Documento Nacional de Identidad"),
    ("CE", "Carné de Extranjería"),
    ("PASAPORTE", "Pasaporte"),
]


def seed(apps, schema_editor):
    InternshipStatus = apps.get_model("internados", "InternshipStatus")
    for codigo, nombre, orden in INTERNSHIP_STATUSES:
        InternshipStatus.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "orden": orden}
        )

    RotationStatus = apps.get_model("internados", "RotationStatus")
    for codigo, nombre, orden in ROTATION_STATUSES:
        RotationStatus.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "orden": orden}
        )

    IdentityDocumentType = apps.get_model("internados", "IdentityDocumentType")
    for codigo, nombre in IDENTITY_DOCUMENT_TYPES:
        IdentityDocumentType.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})


def unseed(apps, schema_editor):
    codes = {
        "InternshipStatus": [r[0] for r in INTERNSHIP_STATUSES],
        "RotationStatus": [r[0] for r in ROTATION_STATUSES],
        "IdentityDocumentType": [r[0] for r in IDENTITY_DOCUMENT_TYPES],
    }
    for model_name, codigos in codes.items():
        Model = apps.get_model("internados", model_name)
        Model.objects.filter(codigo__in=codigos).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
