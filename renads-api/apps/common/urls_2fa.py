"""Rutas de autenticación de dos factores (2FA).

Se incluye desde ``config/api_urls.py`` bajo el prefijo ``auth/``, de modo que
los endpoints quedan en ``/api/v1/auth/2fa/*``.
"""

from django.urls import path

from apps.common.views import (
    TotpConfirmView,
    TotpSetupView,
    TwoFactorDisableView,
    TwoFactorResendView,
    TwoFactorSetupEmailView,
    TwoFactorVerifyView,
)

urlpatterns = [
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="2fa-verify"),
    path("2fa/setup/totp/", TotpSetupView.as_view(), name="2fa-setup-totp"),
    path("2fa/confirm-totp/", TotpConfirmView.as_view(), name="2fa-confirm-totp"),
    path("2fa/setup/email/", TwoFactorSetupEmailView.as_view(), name="2fa-setup-email"),
    path("2fa/resend-otp/", TwoFactorResendView.as_view(), name="2fa-resend-otp"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa-disable"),
]
