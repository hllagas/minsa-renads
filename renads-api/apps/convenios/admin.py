"""Registro en Django admin del módulo Convenios.

Se registran los catálogos de jerarquía geográfica (Red/Microred) y los
catálogos de clasificación de IPRESS (Categoría/Tipo de clasificación).
"""

from django.contrib import admin

from apps.convenios.models import Category, ClassificationType, Microred, Red


@admin.register(Red)
class RedAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "ambito_geografico_sanitario", "activo")
    list_filter = ("ambito_geografico_sanitario", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(Microred)
class MicroredAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "red", "activo")
    list_filter = ("red", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(ClassificationType)
class ClassificationTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
