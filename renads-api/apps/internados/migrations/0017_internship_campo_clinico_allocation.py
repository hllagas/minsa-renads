"""Repunta `Internship.campo_clinico` a la asignación por universidad.

La FK pasa de `campo_clinico_ipress` (registro) a
`campo_clinico_ipress_universidad` (asignación). La columna `campo_clinico_id`
se conserva. La data migration reasigna cada internado existente a la
asignación creada para su antiguo registro en `convenios.0015`
(`ClinicalFieldAllocation.objects.get(campo_clinico_ipress_id=<valor_viejo>)`).
"""

import django.db.models.deletion
from django.db import migrations, models


def repuntar_internados(apps, schema_editor):
    """Reasigna cada internado a la asignación creada para su registro."""
    Internship = apps.get_model("internados", "Internship")
    ClinicalFieldAllocation = apps.get_model("convenios", "ClinicalFieldAllocation")

    for internado in Internship.objects.all():
        registro_id = internado.campo_clinico_id  # apuntaba al viejo registro
        asignacion = ClinicalFieldAllocation.objects.get(
            campo_clinico_ipress_id=registro_id
        )
        internado.campo_clinico_id = asignacion.id
        internado.save(update_fields=["campo_clinico"])


def revertir_internados(apps, schema_editor):
    """Reverso: reapunta el internado al registro padre de su asignación."""
    Internship = apps.get_model("internados", "Internship")
    ClinicalFieldAllocation = apps.get_model("convenios", "ClinicalFieldAllocation")

    for internado in Internship.objects.all():
        asignacion = ClinicalFieldAllocation.objects.get(pk=internado.campo_clinico_id)
        internado.campo_clinico_id = asignacion.campo_clinico_ipress_id
        internado.save(update_fields=["campo_clinico"])


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0015_clinical_field_registration_allocation"),
        ("internados", "0016_remove_student_anio_academico"),
    ]

    operations = [
        # 1. Repuntar las filas ANTES de cambiar el destino de la FK: mientras la FK
        #    apunta al registro, `campo_clinico_id` aún guarda el id del registro,
        #    que es el que resuelve la asignación por `campo_clinico_ipress_id`.
        migrations.RunPython(repuntar_internados, revertir_internados),
        # 2. Cambiar el destino de la FK a la asignación por universidad.
        migrations.AlterField(
            model_name="internship",
            name="campo_clinico",
            field=models.ForeignKey(
                db_column="campo_clinico_id",
                help_text="Asignación de campos clínicos por universidad",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="internos",
                to="convenios.clinicalfieldallocation",
            ),
        ),
    ]
