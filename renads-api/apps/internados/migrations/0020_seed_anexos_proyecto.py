# Siembra los documento_anexo de los PDF generados por el módulo Convenios
# (proyecto de convenio/adenda y expediente consolidado), todos con
# tipo_actor="CONVENIO" y obligatorio=False. Idempotente (get_or_create por codigo).

from django.db import migrations

# (codigo, nombre)
DOCUMENTOS_GENERADOS = [
    ("PROYECTO_CONVENIO", "Proyecto de convenio (PDF generado)"),
    ("PROYECTO_ADENDA", "Proyecto de adenda (PDF generado)"),
    ("EXPEDIENTE", "Expediente del convenio (PDF consolidado)"),
]


def seed(apps, schema_editor):
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    for codigo, nombre in DOCUMENTOS_GENERADOS:
        AnnexDocument.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "tipo_actor": "CONVENIO",
                "obligatorio": False,
                "activo": True,
            },
        )


def unseed(apps, schema_editor):
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    AnnexDocument.objects.filter(
        codigo__in=[c for c, _ in DOCUMENTOS_GENERADOS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0019_annex_actor_convenio_seed"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
