# Amplía ANNEX_ACTOR con CONVENIO / CAMPO_CLINICO y siembra los documento_anexo de
# resolución (RESOL_MARCO/RESOL_ESPECIFICO/RESOL_ADENDA/RESOL_CONAPRES).

from django.db import migrations, models

# (codigo, nombre, tipo_actor)
DOCUMENTOS_RESOLUCION = [
    ("RESOL_MARCO", "Resolución de aprobación del Convenio Marco", "CONVENIO"),
    ("RESOL_ESPECIFICO", "Resolución de aprobación del Convenio Específico", "CONVENIO"),
    ("RESOL_ADENDA", "Resolución de aprobación de la adenda", "CONVENIO"),
    ("RESOL_CONAPRES", "Resolución CONAPRES de campos clínicos", "CAMPO_CLINICO"),
]


def seed(apps, schema_editor):
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    for codigo, nombre, tipo_actor in DOCUMENTOS_RESOLUCION:
        AnnexDocument.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "tipo_actor": tipo_actor,
                "obligatorio": False,
                "activo": True,
            },
        )


def unseed(apps, schema_editor):
    AnnexDocument = apps.get_model("internados", "AnnexDocument")
    AnnexDocument.objects.filter(
        codigo__in=[c for c, *_ in DOCUMENTOS_RESOLUCION]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('internados', '0018_annexdocument_documento_anexo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annexdocument',
            name='tipo_actor',
            field=models.CharField(blank=True, choices=[('INTERNO', 'Interno / estudiante'), ('AUTORIDAD_UNIVERSIDAD', 'Autoridad de universidad'), ('REPRESENTANTE', 'Representante / autoridad (incluye CONAPRES)'), ('CONVENIO', 'Convenio / adenda'), ('CAMPO_CLINICO', 'Campo clínico (resolución CONAPRES)')], default='INTERNO', help_text='Actor que debe presentar el documento (vacío para tipos genéricos)', max_length=30, verbose_name='tipo de actor'),
        ),
        migrations.RunPython(seed, unseed),
    ]
