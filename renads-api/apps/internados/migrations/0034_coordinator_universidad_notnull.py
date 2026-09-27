"""Migración 0034 — Finaliza rediseño Coordinator.universidad.

Parte 2 de 2 (depende de 0033_coordinator_universidad).
Pone NOT NULL, actualiza unique_together de coordinador_sede y elimina
el campo universidad de dicha tabla.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0054_rename_organic_unit"),
        ("internados", "0033_coordinator_universidad"),
    ]

    operations = [
        # 1. AlterField a NOT NULL (el backfill de 0033 garantiza que no haya nulos).
        migrations.AlterField(
            model_name="coordinator",
            name="universidad",
            field=models.ForeignKey(
                db_column="universidad_id",
                help_text="Universidad a la que pertenece el coordinador",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="coordinadores",
                to="convenios.university",
            ),
        ),
        # 2. Actualiza unique_together antes de eliminar el campo.
        migrations.AlterUniqueTogether(
            name="coordinatorsede",
            unique_together={("coordinador", "ipress")},
        ),
        # 3. Elimina universidad de coordinador_sede.
        migrations.RemoveField(
            model_name="coordinatorsede",
            name="universidad",
        ),
    ]
