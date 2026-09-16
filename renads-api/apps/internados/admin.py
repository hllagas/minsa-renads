"""Registro en Django admin del módulo Internados."""

from django.contrib import admin

from apps.internados.models import (
    AnnexDocument,
    IdentityDocumentType,
    Internship,
    InternshipPeriod,
    InternshipStatus,
    InternshipStatusHistory,
    RelationshipType,
    Rotation,
    RotationAuthorization,
    RotationStatus,
    RotationStatusHistory,
    ServiceArea,
    Student,
    Tutor,
    TutorConvenio,
    TutorHistory,
    TutorUniversity,
)


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------
@admin.register(InternshipStatus)
class InternshipStatusAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(RotationStatus)
class RotationStatusAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "orden", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(IdentityDocumentType)
class IdentityDocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(RelationshipType)
class RelationshipTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(InternshipPeriod)
class InternshipPeriodAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(AnnexDocument)
class AnnexDocumentAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo_actor", "obligatorio", "activo")
    list_filter = ("tipo_actor", "obligatorio", "activo")
    search_fields = ("codigo", "nombre")


# ---------------------------------------------------------------------------
# Estudiantes y tutores
# ---------------------------------------------------------------------------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("apellido_paterno", "apellido_materno", "nombres", "numero_documento", "universidad", "carrera_profesional", "nota_promedio_ponderado", "activo")
    list_filter = ("universidad", "carrera_profesional", "sexo", "activo")
    search_fields = ("apellido_paterno", "apellido_materno", "nombres", "numero_documento", "correo")
    readonly_fields = ("creado_en",)


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ("apellido_paterno", "apellido_materno", "nombres", "numero_documento", "numero_colegiatura", "activo")
    list_filter = ("activo", "especialidad")
    search_fields = ("apellido_paterno", "apellido_materno", "nombres", "numero_documento", "numero_colegiatura")


@admin.register(TutorUniversity)
class TutorUniversityAdmin(admin.ModelAdmin):
    list_display = ("tutor", "universidad")
    list_filter = ("universidad",)
    search_fields = ("tutor__apellido_paterno", "universidad__nombre")


@admin.register(TutorConvenio)
class TutorConvenioAdmin(admin.ModelAdmin):
    list_display = ("tutor", "convenio", "ipress")
    list_filter = ("ipress",)
    search_fields = ("tutor__apellido_paterno", "convenio__titulo")


# ---------------------------------------------------------------------------
# Internados
# ---------------------------------------------------------------------------
@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display = ("estudiante", "convenio", "ipress", "tutor", "estado_actual", "estado_declaraciones", "fecha_inicio", "fecha_fin")
    list_filter = ("estado_actual", "estado_declaraciones", "ipress")
    search_fields = ("estudiante__apellido_paterno", "estudiante__numero_documento", "convenio__titulo")
    readonly_fields = ("creado_en", "actualizado_en")
    date_hierarchy = "fecha_inicio"


@admin.register(InternshipStatusHistory)
class InternshipStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("interno", "estado", "cambiado_por", "cambiado_en")
    list_filter = ("estado",)
    search_fields = ("interno__estudiante__apellido_paterno", "cambiado_por__username")
    readonly_fields = ("cambiado_en",)


@admin.register(TutorHistory)
class TutorHistoryAdmin(admin.ModelAdmin):
    list_display = ("interno", "tutor", "fecha_cambio", "responsable")
    search_fields = ("interno__estudiante__apellido_paterno", "tutor__apellido_paterno")
    readonly_fields = ("creado_en",)


# ---------------------------------------------------------------------------
# Rotaciones
# ---------------------------------------------------------------------------
@admin.register(Rotation)
class RotationAdmin(admin.ModelAdmin):
    list_display = ("interno", "numero_rotacion", "ipress_origen", "ipress_destino", "servicio_area", "estado_actual", "fecha_inicio", "fecha_fin")
    list_filter = ("estado_actual", "servicio_area", "numero_rotacion")
    search_fields = ("interno__estudiante__apellido_paterno", "ipress_origen__nombre", "ipress_destino__nombre")
    readonly_fields = ("creado_en",)


@admin.register(RotationAuthorization)
class RotationAuthorizationAdmin(admin.ModelAdmin):
    list_display = ("rotacion", "resultado", "fecha_autorizacion", "autorizado_por")
    list_filter = ("resultado",)
    search_fields = ("rotacion__interno__estudiante__apellido_paterno",)
    readonly_fields = ("creado_en",)


@admin.register(RotationStatusHistory)
class RotationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("rotacion", "estado", "cambiado_por", "cambiado_en")
    list_filter = ("estado",)
    readonly_fields = ("cambiado_en",)
