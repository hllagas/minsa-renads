"""Refactor de contacto de emergencia y profesión de tutor.

1. Mueve los campos de contacto de emergencia de ``interno`` (Internship) a ``estudiante``
   (Student): ``contacto_emergencia_nombre``, ``contacto_emergencia_telefono`` y
   ``contacto_emergencia_parentesco``.

   Historial: migration 0015 los trasladó de ``estudiante`` → ``interno``. Este migration
   los devuelve a ``estudiante``, que es donde conceptualmente pertenecen (son datos del
   estudiante, no del internado particular).

   No se requiere backfill: los campos son opcionales (blank/null) y en dev no hay datos
   de producción; en prod el equipo cargará los datos por el endpoint de estudiantes.

2. Agrega el campo ``profesion`` (FK nullable a ``carrera_profesional``) a ``tutor``.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0050_categoria_rename"),
        ("internados", "0024_ubigeo_fk_codigo"),
    ]

    operations = [
        # ── Contacto de emergencia: estudiante ────────────────────────────────
        migrations.AddField(
            model_name="student",
            name="contacto_emergencia_nombre",
            field=models.CharField(
                verbose_name="contacto de emergencia - nombre",
                max_length=255, blank=True,
                help_text="Nombre del contacto de emergencia",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="contacto_emergencia_telefono",
            field=models.CharField(
                verbose_name="contacto de emergencia - teléfono",
                max_length=30, blank=True,
                help_text="Teléfono del contacto de emergencia",
            ),
        ),
        migrations.AddField(
            model_name="student",
            name="contacto_emergencia_parentesco",
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="contacto_emergencia_parentesco_id",
                to="internados.relationshiptype",
                related_name="+",
                help_text="Parentesco del contacto de emergencia",
            ),
        ),

        # ── Contacto de emergencia: remover de interno ────────────────────────
        migrations.RemoveField(model_name="internship", name="contacto_emergencia_nombre"),
        migrations.RemoveField(model_name="internship", name="contacto_emergencia_telefono"),
        migrations.RemoveField(model_name="internship", name="contacto_emergencia_parentesco"),

        # ── Tutor: agregar profesión ──────────────────────────────────────────
        migrations.AddField(
            model_name="tutor",
            name="profesion",
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                db_column="profesion_id",
                to="convenios.professionalcareer",
                related_name="+",
                help_text="Profesión del tutor (carrera profesional)",
            ),
        ),
    ]
