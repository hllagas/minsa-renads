"""Registro en Django admin de modelos transversales (app common)."""

from django.contrib import admin

from apps.common.models import UserProfile, UserSecurity


@admin.register(UserSecurity)
class UserSecurityAdmin(admin.ModelAdmin):
    list_display = ("usuario", "debe_cambiar_password", "two_factor_enabled", "two_factor_method", "actualizado_en")
    list_filter = ("debe_cambiar_password", "two_factor_enabled", "two_factor_method")
    search_fields = ("usuario__username", "usuario__email")
    readonly_fields = ("actualizado_en", "otp_expires_at", "password_changed_at")
    exclude = ("totp_secret", "otp_code")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo_documento", "numero_documento", "unidad_organica", "cargo")
    list_filter = ("tipo_documento", "unidad_organica")
    search_fields = ("usuario__username", "usuario__last_name", "usuario__first_name", "numero_documento")
