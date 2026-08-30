from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("convenios", "0026_universitycareer_facultad"),
    ]

    operations = [
        # Add fields to RegionalGovernment
        migrations.AddField(
            model_name="regionalgovernment",
            name="numero_ruc",
            field=models.CharField(
                verbose_name="número de RUC",
                max_length=11,
                blank=True,
                default="",
                help_text="RUC (11 dígitos; texto para conservar ceros a la izquierda)",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="regionalgovernment",
            name="direccion",
            field=models.CharField(
                verbose_name="dirección",
                max_length=500,
                blank=True,
                default="",
                help_text="Dirección",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="regionalgovernment",
            name="correo",
            field=models.EmailField(
                verbose_name="correo",
                blank=True,
                default="",
                help_text="Correo institucional",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="regionalgovernment",
            name="telefono",
            field=models.CharField(
                verbose_name="teléfono",
                max_length=30,
                blank=True,
                default="",
                help_text="Teléfono institucional",
            ),
            preserve_default=False,
        ),
        # Remove fields from OrganDirectory
        migrations.RemoveField(
            model_name="organdirectory",
            name="direccion",
        ),
        migrations.RemoveField(
            model_name="organdirectory",
            name="numero_ruc",
        ),
        migrations.RemoveField(
            model_name="organdirectory",
            name="correo",
        ),
        migrations.RemoveField(
            model_name="organdirectory",
            name="telefono_institucional",
        ),
    ]
