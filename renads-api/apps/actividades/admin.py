"""Registro en Django admin del módulo Actividades."""

from django.contrib import admin

from apps.actividades.models import (
    ActivityStatus,
    ActivityStatusHistory,
    ActivityType,
    ActivityValidation,
    TeachingActivity,
)


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(ActivityStatus)
class ActivityStatusAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(TeachingActivity)
class TeachingActivityAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "ipress", "tipo_actividad", "estado_actual", "fecha_actividad", "carga_horaria", "tutor")
    list_filter = ("tipo_actividad", "estado_actual", "ipress")
    search_fields = ("estudiante__apellido_paterno", "estudiante__numero_documento", "ipress__nombre")
    readonly_fields = ("creado_en", "actualizado_en")
    date_hierarchy = "fecha_actividad"


@admin.register(ActivityValidation)
class ActivityValidationAdmin(admin.ModelAdmin):
    list_display = ("actividad", "resultado", "validado_por", "fecha_validacion")
    list_filter = ("resultado",)
    search_fields = ("actividad__estudiante__apellido_paterno", "validado_por__username")
    readonly_fields = ("creado_en",)


@admin.register(ActivityStatusHistory)
class ActivityStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("actividad", "estado", "cambiado_por", "cambiado_en")
    list_filter = ("estado",)
    search_fields = ("actividad__estudiante__apellido_paterno", "cambiado_por__username")
    readonly_fields = ("cambiado_en",)
