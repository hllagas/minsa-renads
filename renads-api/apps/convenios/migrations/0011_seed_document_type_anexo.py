"""Seed idempotente del `DocumentType` `ANEXO` (Etapa 2 — flujo de anexos).

Es el `tipo_documento` por defecto del flujo de adjunto real de anexos
(declaraciones juradas por actor). El mixin `AnnexAttachmentMixin` lo resuelve por
`codigo="ANEXO"` (no por PK).
"""

from django.db import migrations


def crear_document_type_anexo(apps, schema_editor):
    DocumentType = apps.get_model("convenios", "DocumentType")
    DocumentType.objects.get_or_create(
        codigo="ANEXO",
        defaults={"nombre": "Declaración jurada / anexo", "activo": True},
    )


def borrar_document_type_anexo(apps, schema_editor):
    DocumentType = apps.get_model("convenios", "DocumentType")
    DocumentType.objects.filter(codigo="ANEXO").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0010_ipress_logo_document_annex"),
    ]

    operations = [
        migrations.RunPython(crear_document_type_anexo, borrar_document_type_anexo),
    ]
