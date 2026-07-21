"""Modelos transversales (app ``common``).

Nombres de clases en inglés; tablas, columnas y descripciones en español.
"""

from django.conf import settings
from django.db import models


class UserSecurity(models.Model):
    """Ajustes de seguridad por usuario (extensión mínima del User por defecto).

    Django usa ``django.contrib.auth.models.User`` sin modelo custom, por lo que
    el forzado de cambio de contraseña se persiste aquí (relación 1:1) en lugar de
    en la tabla del usuario. Consultable por el front vía el claim del JWT y el
    endpoint ``/api/v1/auth/me/`` (RN-22 — onboarding del interno).
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="usuario_id",
        related_name="seguridad",
        help_text="Usuario asociado",
    )
    debe_cambiar_password = models.BooleanField(
        "debe cambiar contraseña",
        default=False,
        help_text="Obliga al usuario a cambiar su contraseña temporal en el próximo acceso",
    )
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        db_table = "seguridad_usuario"
        verbose_name = "seguridad de usuario"
        verbose_name_plural = "seguridad de usuarios"


def debe_cambiar_password(usuario) -> bool:
    """Indica si el usuario debe cambiar su contraseña (default ``False`` si no hay registro)."""
    seguridad = getattr(usuario, "seguridad", None)
    return bool(seguridad and seguridad.debe_cambiar_password)
