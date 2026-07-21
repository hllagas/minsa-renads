"""Crea los catálogos `periodo_academico` y `documentos_anexos` (F1) y agrega al
estudiante las FKs `periodo_academico` (PROTECT) y `especialidad` (SET_NULL) — RN-19."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0009_rename_nivel_pregrado"),
        ("internados", "0007_remove_student_especialidad"),
    ]

    operations = [
        migrations.CreateModel(
            name="AcademicPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(help_text="Código único", max_length=50, unique=True, verbose_name="código")),
                ("nombre", models.CharField(help_text="Nombre", max_length=255, verbose_name="nombre")),
                ("activo", models.BooleanField(default=True, help_text="Indica si está activo", verbose_name="activo")),
            ],
            options={
                "verbose_name": "periodo académico",
                "db_table": "periodo_academico",
            },
        ),
        migrations.CreateModel(
            name="AnnexDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(help_text="Código único", max_length=50, unique=True, verbose_name="código")),
                ("nombre", models.CharField(help_text="Nombre", max_length=255, verbose_name="nombre")),
                ("activo", models.BooleanField(default=True, help_text="Indica si está activo", verbose_name="activo")),
                ("descripcion", models.TextField(blank=True, help_text="Descripción de la declaración jurada / anexo", verbose_name="descripción")),
                ("obligatorio", models.BooleanField(default=True, help_text="Indica si el anexo es de presentación obligatoria", verbose_name="obligatorio")),
            ],
            options={
                "verbose_name": "documento anexo",
                "db_table": "documentos_anexos",
            },
        ),
        migrations.AddField(
            model_name="student",
            name="periodo_academico",
            field=models.ForeignKey(
                blank=True,
                db_column="periodo_academico_id",
                help_text="Periodo académico (obligatorio para Pregrado — RN-19)",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="internados.academicperiod",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="especialidad",
            field=models.ForeignKey(
                blank=True,
                db_column="especialidad_id",
                help_text="Especialidad (obligatoria para niveles distintos de Pregrado — RN-19)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="convenios.specialty",
            ),
        ),
    ]
