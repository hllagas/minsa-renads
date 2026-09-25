# Endurece `perfil_usuario` — PASO 2 de 2 (schema):
# AlterField de los 7 campos a su estado final NOT NULL. Corre en su propia
# transacción de migración, DESPUÉS de que la 0009 confirmó el backfill de datos,
# evitando el error de PostgreSQL «cannot ALTER TABLE ... because it has pending
# trigger events». En este punto ninguna fila viola el NOT NULL.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0009_userprofile_campos_obligatorios"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="tipo_documento",
            field=models.CharField(
                choices=[
                    ("DNI", "DNI"),
                    ("CE", "Carnet de Extranjería"),
                    ("PASAPORTE", "Pasaporte"),
                    ("RUC", "RUC"),
                ],
                db_column="tipo_documento",
                help_text="Tipo de documento de identidad",
                max_length=20,
                verbose_name="tipo de documento",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="numero_documento",
            field=models.CharField(
                db_column="numero_documento",
                help_text="Número de documento de identidad",
                max_length=20,
                unique=True,
                verbose_name="número de documento",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="apellido_paterno",
            field=models.CharField(
                db_column="apellido_paterno",
                help_text="Apellido paterno del usuario",
                max_length=100,
                verbose_name="apellido paterno",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="apellido_materno",
            field=models.CharField(
                db_column="apellido_materno",
                help_text="Apellido materno del usuario",
                max_length=100,
                verbose_name="apellido materno",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="telefono",
            field=models.CharField(
                db_column="telefono",
                help_text="Número de teléfono de contacto",
                max_length=20,
                unique=True,
                verbose_name="teléfono",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="unidad_organica",
            field=models.ForeignKey(
                db_column="unidad_organica_id",
                help_text="Unidad orgánica a la que pertenece el usuario",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="perfiles_usuarios",
                to="convenios.organicunit",
                verbose_name="unidad orgánica",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="cargo",
            field=models.ForeignKey(
                db_column="cargo_id",
                help_text="Cargo ejecutivo del usuario",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="perfiles_usuarios",
                to="convenios.executiveposition",
                verbose_name="cargo",
            ),
        ),
    ]
