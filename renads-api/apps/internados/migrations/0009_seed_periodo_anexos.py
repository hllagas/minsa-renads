"""Datos semilla de `periodo_academico` (semestres) y `documentos_anexos`
(declaraciones juradas maestras) — F1."""

from django.db import migrations

ACADEMIC_PERIODS = ["2025-I", "2025-II", "2026-I", "2026-II"]

ANNEX_DOCUMENTS = [
    ("DJ_DATOS", "Declaración jurada de veracidad de datos"),
    ("DJ_ANTECEDENTES", "Declaración jurada de no tener antecedentes penales/policiales"),
    ("DJ_SALUD", "Declaración jurada de aptitud de salud"),
    ("DJ_CONFIDENCIALIDAD", "Compromiso de confidencialidad"),
]


def seed(apps, schema_editor):
    AcademicPeriod = apps.get_model("internados", "AcademicPeriod")
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    for codigo in ACADEMIC_PERIODS:
        AcademicPeriod.objects.update_or_create(
            codigo=codigo, defaults={"nombre": f"Semestre {codigo}", "activo": True}
        )
    for codigo, nombre in ANNEX_DOCUMENTS:
        AnnexDocument.objects.update_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "descripcion": nombre, "obligatorio": True, "activo": True},
        )


def unseed(apps, schema_editor):
    AcademicPeriod = apps.get_model("internados", "AcademicPeriod")
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    AcademicPeriod.objects.filter(codigo__in=ACADEMIC_PERIODS).delete()
    AnnexDocument.objects.filter(codigo__in=[c for c, _ in ANNEX_DOCUMENTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0008_academicperiod_annexdocument_student_fks"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
