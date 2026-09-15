# Migración: agrega la columna `fecha_cambio_password` a `seguridad_usuario`.
# Registra cuándo fue el último cambio de contraseña del usuario (T-02 / T-04).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0003_usersecurity_otp_code_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersecurity",
            name="password_changed_at",
            field=models.DateTimeField(
                blank=True,
                db_column="fecha_cambio_password",
                help_text="Fecha y hora del último cambio de contraseña; nulo si nunca se ha cambiado",
                null=True,
                verbose_name="fecha de cambio de contraseña",
            ),
        ),
    ]
