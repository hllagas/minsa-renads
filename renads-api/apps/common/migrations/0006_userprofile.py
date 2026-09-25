# Migración: crea la tabla `perfil_usuario` con los datos personales e
# institucionales adicionales del usuario (1:1 con auth.User).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0005_user_email_unique"),
        ("convenios", "0051_remove_campo_clinico_ipress_convenio"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    # Debe correr antes de que `convenios` renombre OrganDirectory → OrganicUnit
    # (0054). Sin este orden, en un build limpio Django linealiza el rename antes
    # de esta migración y la FK `to='convenios.organdirectory'` no resuelve.
    run_before = [
        ("convenios", "0052_university_entity_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tipo_documento",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("DNI", "DNI"),
                            ("CE", "Carnet de Extranjería"),
                            ("PASAPORTE", "Pasaporte"),
                            ("RUC", "RUC"),
                        ],
                        db_column="tipo_documento",
                        default="",
                        help_text="Tipo de documento de identidad",
                        max_length=20,
                        verbose_name="tipo de documento",
                    ),
                ),
                (
                    "numero_documento",
                    models.CharField(
                        blank=True,
                        db_column="numero_documento",
                        default=None,
                        help_text="Número de documento de identidad",
                        max_length=20,
                        null=True,
                        unique=True,
                        verbose_name="número de documento",
                    ),
                ),
                (
                    "apellido_paterno",
                    models.CharField(
                        blank=True,
                        db_column="apellido_paterno",
                        default="",
                        help_text="Apellido paterno del usuario",
                        max_length=100,
                        verbose_name="apellido paterno",
                    ),
                ),
                (
                    "apellido_materno",
                    models.CharField(
                        blank=True,
                        db_column="apellido_materno",
                        default="",
                        help_text="Apellido materno del usuario",
                        max_length=100,
                        verbose_name="apellido materno",
                    ),
                ),
                (
                    "telefono",
                    models.CharField(
                        blank=True,
                        db_column="telefono",
                        default=None,
                        help_text="Número de teléfono de contacto",
                        max_length=20,
                        null=True,
                        unique=True,
                        verbose_name="teléfono",
                    ),
                ),
                (
                    "cargo",
                    models.ForeignKey(
                        blank=True,
                        db_column="cargo_id",
                        help_text="Cargo ejecutivo del usuario",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="perfiles_usuarios",
                        to="convenios.executiveposition",
                        verbose_name="cargo",
                    ),
                ),
                (
                    "unidad_organica",
                    models.ForeignKey(
                        blank=True,
                        db_column="unidad_organica_id",
                        help_text="Órgano del directorio al que pertenece el usuario",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="perfiles_usuarios",
                        to="convenios.organdirectory",
                        verbose_name="unidad orgánica",
                    ),
                ),
                (
                    "usuario",
                    models.OneToOneField(
                        db_column="usuario_id",
                        help_text="Usuario propietario del perfil",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="perfil",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "perfil de usuario",
                "verbose_name_plural": "perfiles de usuario",
                "db_table": "perfil_usuario",
            },
        ),
    ]
