"""Modelos transversales (app ``common``).

Nombres de clases en inglés; tablas, columnas y descripciones en español.
"""

from django.conf import settings
from django.db import models

# Opciones de método de segundo factor de autenticación.
TWO_FACTOR_METHOD_CHOICES = [
    ("TOTP", "Aplicación TOTP"),
    ("EMAIL", "Correo electrónico"),
]


class UserSecurity(models.Model):
    """Ajustes de seguridad por usuario (extensión mínima del User por defecto).

    Django usa ``django.contrib.auth.models.User`` sin modelo custom, por lo que
    el forzado de cambio de contraseña se persiste aquí (relación 1:1) en lugar de
    en la tabla del usuario. Consultable por el front vía el claim del JWT y el
    endpoint ``/api/v1/auth/me/`` (RN-22 — onboarding del interno).

    Campos 2FA:
    - ``totp_secret`` y ``otp_code`` **nunca** se incluyen en ningún serializer de
      respuesta de la API (contienen datos sensibles: secreto TOTP y hash OTP).
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
    # --- Campos de autenticación de dos factores (2FA) ---
    two_factor_enabled = models.BooleanField(
        "doble factor activo",
        db_column="autenticacion_doble_factor",
        default=False,
        help_text="Indica si el usuario tiene activado el segundo factor de autenticación",
    )
    two_factor_method = models.CharField(
        "método de doble factor",
        db_column="metodo_doble_factor",
        max_length=10,
        choices=TWO_FACTOR_METHOD_CHOICES,
        blank=True,
        default="",
        help_text="Método de segundo factor: TOTP (app autenticadora) o EMAIL (código por correo)",
    )
    # IMPORTANTE: totp_secret NUNCA se expone en ningún serializer de respuesta.
    totp_secret = models.CharField(
        "secreto TOTP",
        db_column="secreto_totp",
        max_length=64,
        blank=True,
        default="",
        help_text="Secreto base32 para generar códigos TOTP; nunca se expone en la API",
    )
    # IMPORTANTE: otp_code almacena el hash SHA-256 del OTP; NUNCA se expone en la API.
    # max_length=64 para alojar el hexdigest SHA-256 completo (64 caracteres hex).
    otp_code = models.CharField(
        "código OTP transitorio",
        db_column="codigo_otp",
        max_length=64,
        blank=True,
        default="",
        help_text="Hash SHA-256 del código OTP de email en tránsito; vacío cuando no hay OTP pendiente",
    )
    otp_expires_at = models.DateTimeField(
        "OTP expira en",
        db_column="otp_expira_en",
        null=True,
        blank=True,
        help_text="Fecha y hora de expiración del OTP de email; nulo si no hay OTP pendiente",
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
