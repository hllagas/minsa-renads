"""Registro en Django admin del módulo Calendario."""

from django.contrib import admin

from apps.calendario.models import CalendarActivity


@admin.register(CalendarActivity)
class CalendarActivityAdmin(admin.ModelAdmin):
    list_display = ("nombre", "numero_orden", "fecha_inicio", "fecha_fin", "controla_acceso", "activo")
    list_filter = ("controla_acceso", "activo")
    search_fields = ("nombre", "responsables")
    filter_horizontal = ("content_types",)
    readonly_fields = ("creado_en", "actualizado_en")
    date_hierarchy = "fecha_inicio"
