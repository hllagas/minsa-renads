"""Migración 0033 — Agrega universidad_id nullable a coordinador y hace backfill.

Parte 1 de 2 (ver 0034_coordinator_universidad_notnull).
Se ejecuta con ``atomic = False`` para poder combinar DDL y DML sin que PostgreSQL
rechace la mezcla de schema-change + RunPython dentro de la misma transacción.
"""

import django.db.models.deletion
from django.db import migrations, models


def _backfill_universidad(apps, schema_editor):
    """Deriva universidad del primer CoordinatorSede del coordinador.

    Los coordinadores sin ninguna sede asignada se eliminan: son registros
    huérfanos que no pueden satisfacer la invariante de negocio (un coordinador
    debe pertenecer a una universidad).
    """
    Coordinator = apps.get_model("internados", "Coordinator")
    CoordinatorSede = apps.get_model("internados", "CoordinatorSede")

    for coordinador in Coordinator.objects.all():
        sede = CoordinatorSede.objects.filter(coordinador=coordinador).first()
        if sede is not None:
            coordinador.universidad_id = sede.universidad_id
            coordinador.save(update_fields=["universidad_id"])
        else:
            # Sin sedes: no se puede derivar universidad → se elimina el huérfano.
            coordinador.delete()


def _noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    atomic = False  # necesario para combinar DDL y DML en PostgreSQL sin «pending trigger events»

    dependencies = [
        ("convenios", "0054_rename_organic_unit"),
        ("internados", "0032_coordinador"),
    ]

    operations = [
        # 1. Agrega el campo nullable.
        migrations.AddField(
            model_name="coordinator",
            name="universidad",
            field=models.ForeignKey(
                blank=True,
                db_column="universidad_id",
                help_text="Universidad a la que pertenece el coordinador",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="coordinadores",
                to="convenios.university",
            ),
        ),
        # 2. Backfill — debe ejecutarse en transacción separada de las DDL.
        migrations.RunPython(_backfill_universidad, reverse_code=_noop),
    ]
