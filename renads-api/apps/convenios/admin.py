"""Registro en Django admin del módulo Convenios."""

from django.contrib import admin

from apps.convenios.models import (
    AcademicLevel,
    AuditLog,
    AuthorizationType,
    Category,
    ClassificationType,
    ClosureReason,
    ClinicalFieldAllocation,
    ClinicalFieldRegistration,
    Conapres,
    ConapresOpinion,
    Convention,
    ConventionParticipant,
    ConventionParty,
    ConventionStatus,
    ConventionStatusHistory,
    ConventionTemplate,
    ConventionType,
    Document,
    ExecutingUnit,
    ExecutivePosition,
    Faculty,
    HealthGeographicScope,
    Ipress,
    LegalOpinion,
    Microred,
    ObservationReason,
    Organ,
    OrganicUnit,
    OrganRepresentative,
    OrganRepresentativeHistory,
    ProfessionalCareer,
    Publication,
    Red,
    Region,
    RegionalGovernment,
    RejectionReason,
    Signature,
    SigningAuthorityType,
    Specialty,
    TechnicalEvaluation,
    Ubigeo,
    University,
    UniversityCareer,
    UniversityCampus,
    UniversityManagementType,
    UserEntityProfile,
)


# ---------------------------------------------------------------------------
# Catálogos simples
# ---------------------------------------------------------------------------
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(HealthGeographicScope)
class HealthGeographicScopeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "gobierno_regional", "activo")
    list_filter = ("activo", "gobierno_regional")
    search_fields = ("codigo", "nombre")


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


@admin.register(ConventionType)
class ConventionTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "anios_vigencia", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(ConventionStatus)
class ConventionStatusAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "aplica_a", "orden", "activo")
    list_filter = ("aplica_a", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(UniversityManagementType)
class UniversityManagementTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(AuthorizationType)
class AuthorizationTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(AcademicLevel)
class AcademicLevelAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(SigningAuthorityType)
class SigningAuthorityTypeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(ObservationReason)
class ObservationReasonAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(RejectionReason)
class RejectionReasonAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(ClosureReason)
class ClosureReasonAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
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


# ---------------------------------------------------------------------------
# Ubigeo
# ---------------------------------------------------------------------------
@admin.register(Ubigeo)
class UbigeoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "departamento", "provincia", "distrito", "activo")
    list_filter = ("departamento", "activo")
    search_fields = ("codigo", "departamento", "provincia", "distrito")


# ---------------------------------------------------------------------------
# Órganos e instituciones
# ---------------------------------------------------------------------------
@admin.register(Organ)
class OrganAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado")
    list_filter = ("estado",)
    search_fields = ("nombre",)


@admin.register(ExecutivePosition)
class ExecutivePositionAdmin(admin.ModelAdmin):
    list_display = ("nombre_masculino", "nombre_femenino", "organo", "unidad_organica", "activo")
    list_filter = ("organo", "activo")
    search_fields = ("nombre_masculino", "nombre_femenino")


@admin.register(RegionalGovernment)
class RegionalGovernmentAdmin(admin.ModelAdmin):
    list_display = ("nombre", "sigla", "region", "numero_ruc", "activo")
    list_filter = ("region", "activo")
    search_fields = ("nombre", "sigla", "numero_ruc")


@admin.register(OrganicUnit)
class OrganicUnitAdmin(admin.ModelAdmin):
    list_display = ("nombre", "siglas", "organo", "activo")
    list_filter = ("organo", "activo")
    search_fields = ("nombre", "siglas")


@admin.register(ExecutingUnit)
class ExecutingUnitAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "ambito_geografico_sanitario", "activo")
    list_filter = ("ambito_geografico_sanitario", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(Ipress)
class IpressAdmin(admin.ModelAdmin):
    list_display = ("codigo_renipress", "nombre", "unidad_ejecutora", "ambito_geografico_sanitario", "es_sede_docente", "activo")
    list_filter = ("unidad_ejecutora", "ambito_geografico_sanitario", "es_sede_docente", "activo")
    search_fields = ("codigo_renipress", "nombre", "numero_ruc")


@admin.register(Conapres)
class ConapresAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre",)


@admin.register(OrganRepresentative)
class OrganRepresentativeAdmin(admin.ModelAdmin):
    list_display = ("nombre", "numero_documento_identidad", "cargo_ejecutivo", "sexo", "fecha_inicio_designacion", "activo")
    list_filter = ("sexo", "activo", "cargo_ejecutivo")
    search_fields = ("nombre", "numero_documento_identidad")


@admin.register(OrganRepresentativeHistory)
class OrganRepresentativeHistoryAdmin(admin.ModelAdmin):
    list_display = ("nombre", "numero_documento_identidad", "cargo_ejecutivo", "fecha_baja")
    list_filter = ("cargo_ejecutivo",)
    search_fields = ("nombre", "numero_documento_identidad")
    readonly_fields = ("creado_en",)


# ---------------------------------------------------------------------------
# Universidades
# ---------------------------------------------------------------------------
@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("nombre", "siglas", "tipo_gestion", "tipo_autorizacion", "activo")
    list_filter = ("tipo_gestion", "tipo_autorizacion", "activo")
    search_fields = ("nombre", "siglas", "numero_ruc", "codigo_inei")


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("nombre", "universidad", "activo")
    list_filter = ("universidad", "activo")
    search_fields = ("nombre",)


@admin.register(ProfessionalCareer)
class ProfessionalCareerAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nivel_academico", "activo")
    list_filter = ("nivel_academico", "activo")
    search_fields = ("nombre",)


@admin.register(UniversityCareer)
class UniversityCareerAdmin(admin.ModelAdmin):
    list_display = ("universidad", "carrera_profesional", "facultad", "activo")
    list_filter = ("universidad", "facultad", "activo")
    search_fields = ("universidad__nombre", "carrera_profesional__nombre")


@admin.register(UniversityCampus)
class UniversityCampusAdmin(admin.ModelAdmin):
    list_display = ("nombre", "universidad", "region", "activo")
    list_filter = ("universidad", "region", "activo")
    search_fields = ("nombre", "direccion")


# ---------------------------------------------------------------------------
# Seguridad y perfiles
# ---------------------------------------------------------------------------
@admin.register(UserEntityProfile)
class UserEntityProfileAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo_contenido", "id_objeto", "grupo", "activo")
    list_filter = ("tipo_contenido", "grupo", "activo")
    search_fields = ("usuario__username", "id_objeto")


# ---------------------------------------------------------------------------
# Convenios
# ---------------------------------------------------------------------------
@admin.register(ConventionTemplate)
class ConventionTemplateAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo_convenio", "version", "activo", "creado_en")
    list_filter = ("tipo_convenio", "activo")
    search_fields = ("nombre",)


@admin.register(Convention)
class ConventionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo_convenio", "universidad", "unidad_organica", "estado_actual", "fecha_solicitud", "es_adenda")
    list_filter = ("tipo_convenio", "estado_actual", "es_adenda")
    search_fields = ("titulo", "nomenclatura", "universidad__nombre")
    readonly_fields = ("creado_en", "actualizado_en")
    date_hierarchy = "fecha_solicitud"


@admin.register(ConventionParticipant)
class ConventionParticipantAdmin(admin.ModelAdmin):
    list_display = ("convenio", "tipo_contenido", "id_objeto", "es_firmante", "creado_en")
    list_filter = ("tipo_contenido", "es_firmante")
    search_fields = ("convenio__titulo",)


@admin.register(ConventionParty)
class ConventionPartyAdmin(admin.ModelAdmin):
    list_display = ("convenio", "rol", "unidad_organica", "organo_representante", "orden", "es_firmante")
    list_filter = ("rol", "es_firmante")
    search_fields = ("convenio__titulo", "unidad_organica__nombre")


@admin.register(ConventionStatusHistory)
class ConventionStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("convenio", "estado", "cambiado_por", "cambiado_en")
    list_filter = ("estado",)
    search_fields = ("convenio__titulo", "cambiado_por__username")
    readonly_fields = ("cambiado_en",)


# ---------------------------------------------------------------------------
# Flujo del convenio
# ---------------------------------------------------------------------------
@admin.register(TechnicalEvaluation)
class TechnicalEvaluationAdmin(admin.ModelAdmin):
    list_display = ("convenio", "resultado", "fecha_evaluacion", "evaluado_por")
    list_filter = ("resultado",)
    search_fields = ("convenio__titulo", "evaluado_por__username")
    readonly_fields = ("creado_en",)


@admin.register(ConapresOpinion)
class ConapresOpinionAdmin(admin.ModelAdmin):
    list_display = ("convenio", "resultado_opinion", "fecha_solicitud", "fecha_respuesta")
    list_filter = ("resultado_opinion",)
    search_fields = ("convenio__titulo",)


@admin.register(ClinicalFieldRegistration)
class ClinicalFieldRegistrationAdmin(admin.ModelAdmin):
    list_display = ("ipress", "carrera_profesional", "campos_clinicos_registrados", "campos_clinicos_asignados", "numero_resolucion_conapres")
    list_filter = ("carrera_profesional",)
    search_fields = ("ipress__nombre", "ipress__codigo_renipress", "numero_resolucion_conapres")
    readonly_fields = ("campos_clinicos_asignados", "creado_en", "actualizado_en")


@admin.register(ClinicalFieldAllocation)
class ClinicalFieldAllocationAdmin(admin.ModelAdmin):
    list_display = ("ipress", "carrera_profesional", "universidad", "convenio", "campos_clinicos_autorizados", "fecha_inicio", "fecha_fin")
    list_filter = ("universidad", "carrera_profesional")
    search_fields = ("ipress__nombre", "universidad__nombre", "convenio__titulo")
    readonly_fields = ("creado_en", "actualizado_en")


@admin.register(LegalOpinion)
class LegalOpinionAdmin(admin.ModelAdmin):
    list_display = ("convenio", "resultado_opinion", "fecha_envio", "fecha_respuesta")
    list_filter = ("resultado_opinion",)
    search_fields = ("convenio__titulo",)


@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ("convenio", "estado_firma", "orden_firma", "fecha_envio", "fecha_recepcion")
    list_filter = ("estado_firma",)
    search_fields = ("convenio__titulo",)
    readonly_fields = ("creado_en",)


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("convenio", "fecha_publicacion", "creado_por")
    search_fields = ("convenio__titulo", "referencia_publicacion")
    readonly_fields = ("creado_en",)


# ---------------------------------------------------------------------------
# Documentos y auditoría
# ---------------------------------------------------------------------------
@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("tipo_contenido", "id_objeto", "documento_anexo", "version", "estado", "cargado_por", "cargado_en")
    list_filter = ("estado", "tipo_contenido")
    search_fields = ("referencia_externa", "cargado_por__username")
    readonly_fields = ("cargado_en",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("accion", "tipo_contenido", "id_objeto", "nombre_campo", "usuario", "creado_en")
    list_filter = ("accion", "tipo_contenido")
    search_fields = ("id_objeto", "usuario__username", "nombre_campo")
    readonly_fields = ("creado_en",)
