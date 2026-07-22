from django.db import migrations


class Migration(migrations.Migration):
    """Elimina la columna redundante `anio_academico` de `estudiante` (F6).

    El año/periodo lectivo queda representado únicamente por `periodo_academico`
    (FK → `periodo_academico`). El drop elimina la columna y cualquier dato
    existente de forma intencional e irreversible (dato reconstruible desde
    `periodo_academico`).
    """

    dependencies = [
        ("internados", "0015_move_emergency_contact_to_internship"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="student",
            name="anio_academico",
        ),
    ]
