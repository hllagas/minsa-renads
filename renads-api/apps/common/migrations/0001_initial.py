"""Migración inicial de la app transversal `common`: modelo `UserSecurity`."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSecurity",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "debe_cambiar_password",
                    models.BooleanField(
                        default=False,
                        help_text="Obliga al usuario a cambiar su contraseña temporal en el próximo acceso",
                        verbose_name="debe cambiar contraseña",
                    ),
                ),
                ("actualizado_en", models.DateTimeField(auto_now=True, verbose_name="actualizado en")),
                (
                    "usuario",
                    models.OneToOneField(
                        db_column="usuario_id",
                        help_text="Usuario asociado",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seguridad",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "seguridad de usuario",
                "verbose_name_plural": "seguridad de usuarios",
                "db_table": "seguridad_usuario",
            },
        ),
    ]
