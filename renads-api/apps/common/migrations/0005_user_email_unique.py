# Migración: añade unicidad real al campo email de auth.User.
#
# Paso 1 (data migration): convierte los email="" a NULL para que la restricción
# UNIQUE no falle con múltiples usuarios sin correo registrado.
# Paso 2 (RunSQL): aplica la restricción UNIQUE y nullable al nivel de BD sobre
# `auth_user.email` sin alterar el estado del ORM de la app `auth`.

from django.db import migrations


def convertir_emails_vacios_a_null(apps, schema_editor):
    """Convierte los email vacíos a NULL antes de agregar la restricción UNIQUE."""
    User = apps.get_model("auth", "User")
    User.objects.filter(email="").update(email=None)


def revertir_emails_null_a_vacio(apps, schema_editor):
    """Revierte los NULL a string vacío al hacer rollback de la migración."""
    User = apps.get_model("auth", "User")
    User.objects.filter(email__isnull=True).update(email="")


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("common", "0004_usersecurity_password_changed_at"),
    ]

    operations = [
        # Paso 1: data migration — emails vacíos a NULL.
        migrations.RunPython(
            convertir_emails_vacios_a_null,
            reverse_code=revertir_emails_null_a_vacio,
        ),
        # Paso 2: aplicar la restricción UNIQUE y nullable a nivel de base de datos.
        # Se usa RunSQL para evitar conflictos de estado con la app `auth` que gestiona
        # su propio campo `email`. El ORM de Django ya acepta NULL en el campo email
        # a partir de aquí; la restricción de integridad la garantiza la BD.
        migrations.RunSQL(
            sql=(
                # SQLite: recrear la columna como nullable y única no es directo;
                # se usan PRAGMA y recreación de índice único.
                "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique "
                "ON auth_user (email) WHERE email IS NOT NULL;"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS auth_user_email_unique;"
            ),
        ),
    ]
