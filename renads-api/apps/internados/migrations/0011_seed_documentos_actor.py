"""Datos semilla de `documentos_anexos` por actor: resolución del cargo y documento
de identidad para autoridades de universidad y representantes (incluye CONAPRES)."""

from django.db import migrations

# (codigo, nombre, descripcion, tipo_actor)
DOCUMENTOS_ACTOR = [
    (
        "RESOL_AUTUNI",
        "Resolución de designación del cargo",
        "Resolución que acredita la designación en el cargo de la autoridad de universidad",
        "AUTORIDAD_UNIVERSIDAD",
    ),
    (
        "DNI_AUTUNI",
        "Documento de identidad",
        "Documento nacional de identidad de la autoridad de universidad",
        "AUTORIDAD_UNIVERSIDAD",
    ),
    (
        "RESOL_REP",
        "Resolución de designación del cargo",
        "Resolución que acredita la designación en el cargo del representante (incluye CONAPRES)",
        "REPRESENTANTE",
    ),
    (
        "DNI_REP",
        "Documento de identidad",
        "Documento nacional de identidad del representante (incluye CONAPRES)",
        "REPRESENTANTE",
    ),
]


def seed(apps, schema_editor):
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    for codigo, nombre, descripcion, tipo_actor in DOCUMENTOS_ACTOR:
        AnnexDocument.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "descripcion": descripcion,
                "tipo_actor": tipo_actor,
                "obligatorio": True,
                "activo": True,
            },
        )


def unseed(apps, schema_editor):
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    AnnexDocument.objects.filter(codigo__in=[c for c, *_ in DOCUMENTOS_ACTOR]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0010_annexdocument_tipo_actor"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
