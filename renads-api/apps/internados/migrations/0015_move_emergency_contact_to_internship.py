"""Mueve el contacto de emergencia de `estudiante` a `interno` y re-apunta las
declaraciones juradas (anexos del actor INTERNO) del estudiante al internado.

- Agrega `contacto_emergencia_nombre/telefono/parentesco` a `interno` (M2).
- Copia los valores existentes desde el `estudiante` a cada `interno`.
- Re-apunta los `documento` de anexos del actor INTERNO desde `estudiante` a su
  internado (al internado más reciente del estudiante, best-effort).
- Elimina las columnas de contacto de emergencia de `estudiante`.
"""

import django.db.models.deletion
from django.db import migrations, models


def copiar_contacto_y_reapuntar_anexos(apps, schema_editor):
    Student = apps.get_model("internados", "Student")
    Internship = apps.get_model("internados", "Internship")
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    Document = apps.get_model("convenios", "Document")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # 1) Copiar el contacto de emergencia del estudiante a cada internado.
    for interno in Internship.objects.all().iterator():
        estudiante = Student.objects.filter(pk=interno.estudiante_id).first()
        if estudiante is None:
            continue
        interno.contacto_emergencia_nombre = estudiante.contacto_emergencia_nombre or ""
        interno.contacto_emergencia_telefono = estudiante.contacto_emergencia_telefono or ""
        interno.contacto_emergencia_parentesco_id = estudiante.contacto_emergencia_parentesco_id
        interno.save(
            update_fields=[
                "contacto_emergencia_nombre",
                "contacto_emergencia_telefono",
                "contacto_emergencia_parentesco",
            ]
        )

    # 2) Re-apuntar los anexos del actor INTERNO del estudiante a su internado.
    ct_student = ContentType.objects.filter(app_label="internados", model="student").first()
    ct_interno = ContentType.objects.filter(app_label="internados", model="internship").first()
    if not ct_student or not ct_interno:
        return
    anexos_interno = set(
        AnnexDocument.objects.filter(tipo_actor="INTERNO").values_list("id", flat=True)
    )
    if not anexos_interno:
        return
    documentos = Document.objects.filter(
        tipo_contenido_id=ct_student.id,
        documento_anexo_id__in=anexos_interno,
    )
    for doc in documentos.iterator():
        interno = (
            Internship.objects.filter(estudiante_id=doc.id_objeto).order_by("-id").first()
        )
        if interno is None:
            continue  # estudiante sin internado: se deja como estaba
        doc.tipo_contenido_id = ct_interno.id
        doc.id_objeto = interno.id
        doc.save(update_fields=["tipo_contenido", "id_objeto"])


def revertir(apps, schema_editor):
    """Copia de vuelta el contacto de emergencia del internado al estudiante.

    (No re-apunta los documentos: la reversión de datos es best-effort.)
    """
    Student = apps.get_model("internados", "Student")
    Internship = apps.get_model("internados", "Internship")
    for interno in Internship.objects.all().iterator():
        estudiante = Student.objects.filter(pk=interno.estudiante_id).first()
        if estudiante is None:
            continue
        estudiante.contacto_emergencia_nombre = interno.contacto_emergencia_nombre or ""
        estudiante.contacto_emergencia_telefono = interno.contacto_emergencia_telefono or ""
        estudiante.contacto_emergencia_parentesco_id = interno.contacto_emergencia_parentesco_id
        estudiante.save(
            update_fields=[
                "contacto_emergencia_nombre",
                "contacto_emergencia_telefono",
                "contacto_emergencia_parentesco",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0014_tutor_universidades"),
        ("convenios", "0011_seed_document_type_anexo"),
    ]

    operations = [
        migrations.AddField(
            model_name="internship",
            name="contacto_emergencia_nombre",
            field=models.CharField(
                blank=True, default="", help_text="Nombre del contacto de emergencia",
                max_length=255, verbose_name="contacto de emergencia - nombre",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="internship",
            name="contacto_emergencia_telefono",
            field=models.CharField(
                blank=True, default="", help_text="Teléfono del contacto de emergencia",
                max_length=30, verbose_name="contacto de emergencia - teléfono",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="internship",
            name="contacto_emergencia_parentesco",
            field=models.ForeignKey(
                blank=True, db_column="contacto_emergencia_parentesco_id",
                help_text="Parentesco del contacto de emergencia", null=True,
                on_delete=django.db.models.deletion.PROTECT, related_name="+",
                to="internados.relationshiptype",
            ),
        ),
        migrations.RunPython(copiar_contacto_y_reapuntar_anexos, revertir),
        migrations.RemoveField(model_name="student", name="contacto_emergencia_nombre"),
        migrations.RemoveField(model_name="student", name="contacto_emergencia_telefono"),
        migrations.RemoveField(model_name="student", name="contacto_emergencia_parentesco"),
    ]
