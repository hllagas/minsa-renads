"""Renombra `interno` → `estudiante`, agrega campos (nota, contacto de emergencia)
y crea el catálogo `parentesco`."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0003_intern_direccion_intern_ubigeo_tutor_direccion_and_more"),
    ]

    operations = [
        # Nuevo catálogo de parentesco (contacto de emergencia).
        migrations.CreateModel(
            name="RelationshipType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(help_text="Código único", max_length=50, unique=True, verbose_name="código")),
                ("nombre", models.CharField(help_text="Nombre", max_length=255, verbose_name="nombre")),
                ("activo", models.BooleanField(default=True, help_text="Indica si está activo", verbose_name="activo")),
            ],
            options={
                "verbose_name": "tipo de parentesco",
                "db_table": "parentesco",
            },
        ),
        # Renombrado del modelo y su tabla: Intern → Student / interno → estudiante.
        migrations.RenameModel(old_name="Intern", new_name="Student"),
        migrations.AlterModelTable(name="student", table="estudiante"),
        migrations.AlterModelOptions(
            name="student",
            options={"verbose_name": "estudiante"},
        ),
        migrations.AlterField(
            model_name="student",
            name="universidad",
            field=models.ForeignKey(
                db_column="universidad_id", help_text="Universidad de procedencia",
                on_delete=django.db.models.deletion.PROTECT, related_name="estudiantes",
                to="convenios.university",
            ),
        ),
        # Nuevos campos del estudiante.
        migrations.AddField(
            model_name="student",
            name="nota_promedio_ponderado",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Nota promedio ponderado (escala 0–20)",
                max_digits=4, null=True, verbose_name="nota promedio ponderado",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="contacto_emergencia_nombre",
            field=models.CharField(
                blank=True, help_text="Nombre del contacto de emergencia", max_length=255,
                verbose_name="contacto de emergencia - nombre",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="contacto_emergencia_telefono",
            field=models.CharField(
                blank=True, help_text="Teléfono del contacto de emergencia", max_length=30,
                verbose_name="contacto de emergencia - teléfono",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="contacto_emergencia_parentesco",
            field=models.ForeignKey(
                blank=True, db_column="contacto_emergencia_parentesco_id",
                help_text="Parentesco del contacto de emergencia", null=True,
                on_delete=django.db.models.deletion.PROTECT, related_name="+",
                to="internados.relationshiptype",
            ),
        ),
        # FK del internado a la persona: interno → estudiante / interno_id → estudiante_id.
        migrations.RenameField(model_name="internship", old_name="interno", new_name="estudiante"),
        migrations.AlterField(
            model_name="internship",
            name="estudiante",
            field=models.ForeignKey(
                db_column="estudiante_id", help_text="Estudiante",
                on_delete=django.db.models.deletion.PROTECT, related_name="internados",
                to="internados.student",
            ),
        ),
    ]
