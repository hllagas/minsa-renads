"""Corrige el catálogo de tipos de documento: activos DNI y PASAPORTE; CE inactivo.

La regla de negocio de internados solo admite DNI y Pasaporte. Algunos entornos quedaron
sin PASAPORTE (la fila se agregó al seed 0002 después de su aplicación) y con CE activo.
Se asegura PASAPORTE, se activa DNI y se desactiva CE (sin borrar, por integridad referencial).
"""

from django.db import migrations


def fix(apps, schema_editor):
    T = apps.get_model("internados", "IdentityDocumentType")
    T.objects.update_or_create(codigo="PASAPORTE", defaults={"nombre": "Pasaporte", "activo": True})
    T.objects.filter(codigo="DNI").update(activo=True)
    T.objects.filter(codigo="CE").update(activo=False)


def unfix(apps, schema_editor):
    # Reactiva CE (no elimina PASAPORTE: es dato válido del catálogo).
    T = apps.get_model("internados", "IdentityDocumentType")
    T.objects.filter(codigo="CE").update(activo=True)


class Migration(migrations.Migration):

    dependencies = [
        ("internados", "0030_student_nota_decimal4_validators"),
    ]

    operations = [
        migrations.RunPython(fix, unfix),
    ]
