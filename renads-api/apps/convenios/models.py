"""Modelos del Módulo 1: Gestionar Convenios.

Nombres de clases en inglés; tablas, columnas y descripciones en español.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


# ---------------------------------------------------------------------------
# Base de catálogos
# ---------------------------------------------------------------------------
class Catalog(models.Model):
    """Base abstracta para tablas paramétricas (RNF-MAN-01)."""

    codigo = models.CharField("código", max_length=50, unique=True, help_text="Código único")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre")
    activo = models.BooleanField("activo", default=True, help_text="Indica si está activo")

    class Meta:
        abstract = True

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------
class Region(Catalog):
    class Meta:
        db_table = "region"
        verbose_name = "región"
        verbose_name_plural = "regiones"


class HealthGeographicScope(Catalog):
    class Meta:
        db_table = "ambito_geografico_sanitario"
        verbose_name = "ámbito geográfico sanitario"


class ConventionType(Catalog):
    anios_vigencia = models.PositiveSmallIntegerField(
        "años de vigencia", help_text="Vigencia en años (Marco=4, Específico=3)"
    )

    class Meta:
        db_table = "tipo_convenio"
        verbose_name = "tipo de convenio"


APLICA_A = [("TODOS", "Todos"), ("ESPECIFICO", "Específico")]


class ConventionStatus(Catalog):
    aplica_a = models.CharField(
        "aplica a", max_length=20, choices=APLICA_A, default="TODOS",
        help_text="Tipo de convenio al que aplica el estado",
    )
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Orden en el flujo")

    class Meta:
        db_table = "estado_convenio"
        verbose_name = "estado de convenio"


class DocumentType(Catalog):
    class Meta:
        db_table = "tipo_documento"
        verbose_name = "tipo de documento"


class UniversityManagementType(Catalog):
    class Meta:
        db_table = "tipo_gestion_universidad"
        verbose_name = "tipo de gestión de universidad"


class UniversityEntityType(Catalog):
    class Meta:
        db_table = "tipo_entidad_universidad"
        verbose_name = "tipo de entidad de universidad"


class AuthorizationType(Catalog):
    class Meta:
        db_table = "tipo_autorizacion"
        verbose_name = "tipo de autorización"


class AcademicLevel(Catalog):
    class Meta:
        db_table = "nivel_academico"
        verbose_name = "nivel académico"


class Specialty(Catalog):
    class Meta:
        db_table = "especialidad"
        verbose_name = "especialidad"


class SigningAuthorityType(Catalog):
    class Meta:
        db_table = "tipo_autoridad_firmante"
        verbose_name = "tipo de autoridad firmante"


class RegionalOrganType(Catalog):
    class Meta:
        db_table = "tipo_organo_regional"
        verbose_name = "tipo de órgano regional"


class ExecutingUnitType(Catalog):
    class Meta:
        db_table = "tipo_unidad_ejecutora"
        verbose_name = "tipo de unidad ejecutora"


class MinsaOrganType(Catalog):
    class Meta:
        db_table = "tipo_organo_minsa"
        verbose_name = "tipo de órgano del MINSA"


class ExecutivePosition(Catalog):
    class Meta:
        db_table = "cargo_ejecutivo"
        verbose_name = "cargo ejecutivo"


class ObservationReason(Catalog):
    class Meta:
        db_table = "motivo_observacion"
        verbose_name = "motivo de observación"


class RejectionReason(Catalog):
    class Meta:
        db_table = "motivo_rechazo"
        verbose_name = "motivo de rechazo"


class ClosureReason(Catalog):
    class Meta:
        db_table = "motivo_cierre"
        verbose_name = "motivo de cierre"


# ---------------------------------------------------------------------------
# Ubigeo (INEI)
# ---------------------------------------------------------------------------
class Ubigeo(models.Model):
    """Ubicación geográfica del Perú a nivel distrito (código UBIGEO del INEI)."""

    codigo = models.CharField("código", max_length=6, unique=True, help_text="Código UBIGEO INEI (6 dígitos)")
    departamento = models.CharField("departamento", max_length=100, help_text="Departamento")
    provincia = models.CharField("provincia", max_length=100, help_text="Provincia")
    distrito = models.CharField("distrito", max_length=100, help_text="Distrito")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "ubigeo"
        verbose_name = "ubigeo"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.departamento} / {self.provincia} / {self.distrito}"


# ---------------------------------------------------------------------------
# Entidades — Gobiernos Regionales (GORE)
# ---------------------------------------------------------------------------
class RegionalGovernment(models.Model):
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del gobierno regional")
    region = models.ForeignKey(Region, on_delete=models.PROTECT, db_column="region_id", help_text="Región")
    referencia_logo = models.CharField(
        "referencia del logo", max_length=500, blank=True,
        help_text="Referencia externa del logo (repositorio externo)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "gobierno_regional"
        verbose_name = "gobierno regional"

    def __str__(self):
        return self.nombre


class RegionalOrgan(models.Model):
    gobierno_regional = models.ForeignKey(
        RegionalGovernment, on_delete=models.PROTECT, db_column="gobierno_regional_id",
        related_name="organos", help_text="GORE al que pertenece",
    )
    tipo_organo_regional = models.ForeignKey(
        RegionalOrganType, on_delete=models.PROTECT, db_column="tipo_organo_regional_id",
        help_text="GERESA / DIRESA / DIRIS",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del órgano")
    siglas = models.CharField("siglas", max_length=50, blank=True, help_text="Siglas")
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    referencia_logo = models.CharField(
        "referencia del logo", max_length=500, blank=True,
        help_text="Referencia externa del logo (repositorio externo)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "organo_regional"
        verbose_name = "órgano regional"

    def __str__(self):
        return self.nombre


class ExecutingUnit(models.Model):
    organo_regional = models.ForeignKey(
        RegionalOrgan, on_delete=models.PROTECT, db_column="organo_regional_id",
        related_name="unidades_ejecutoras", help_text="Órgano regional que la administra",
    )
    tipo_unidad_ejecutora = models.ForeignKey(
        ExecutingUnitType, on_delete=models.PROTECT, db_column="tipo_unidad_ejecutora_id",
        help_text="Hospital / Instituto / Red",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre")
    codigo = models.CharField("código", max_length=50, blank=True, help_text="Código presupuestal")
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    referencia_logo = models.CharField(
        "referencia del logo", max_length=500, blank=True,
        help_text="Referencia externa del logo (repositorio externo)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "unidad_ejecutora"
        verbose_name = "unidad ejecutora"

    def __str__(self):
        return self.nombre


class Ipress(models.Model):
    unidad_ejecutora = models.ForeignKey(
        ExecutingUnit, on_delete=models.PROTECT, db_column="unidad_ejecutora_id",
        related_name="ipress", help_text="Unidad ejecutora a la que pertenece",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del establecimiento")
    codigo_renipress = models.CharField("código RENIPRESS", max_length=20, blank=True, help_text="Código RENIPRESS")
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    ambito_geografico_sanitario = models.ForeignKey(
        HealthGeographicScope, on_delete=models.PROTECT, db_column="ambito_geografico_sanitario_id",
        help_text="Ámbito geográfico sanitario",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "ipress"
        verbose_name = "IPRESS"
        verbose_name_plural = "IPRESS"

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Entidades — MINSA
# ---------------------------------------------------------------------------
class MinsaOrgan(models.Model):
    tipo_organo_minsa = models.ForeignKey(
        MinsaOrganType, on_delete=models.PROTECT, db_column="tipo_organo_minsa_id",
        help_text="DIGEP / OGAJ / SG / VICEPAS",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del órgano")
    siglas = models.CharField("siglas", max_length=50, blank=True, help_text="Siglas")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "organo_minsa"
        verbose_name = "órgano del MINSA"

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Entidades — CONAPRES
# ---------------------------------------------------------------------------
class Conapres(models.Model):
    nombre = models.CharField("nombre", max_length=255, help_text="Denominación")
    descripcion = models.TextField("descripción", blank=True, help_text="Descripción")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "conapres"
        verbose_name = "CONAPRES"

    def __str__(self):
        return self.nombre


REPRESENTATIVE_ORIGIN = [
    ("MINSA", "MINSA"),
    ("GOBIERNO_REGIONAL", "Gobierno Regional"),
    ("ASOCIACION_FACULTADES", "Asociación de Facultades"),
]


class Representative(models.Model):
    """Representante/autoridad genérico de una entidad (relación polimórfica)."""

    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_column="tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad representada",
    )
    id_objeto = models.PositiveBigIntegerField("id objeto", help_text="Identificador de la entidad representada")
    entidad = GenericForeignKey("tipo_contenido", "id_objeto")
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del representante")
    cargo_ejecutivo = models.ForeignKey(
        ExecutivePosition, on_delete=models.PROTECT, db_column="cargo_ejecutivo_id",
        help_text="Cargo (catálogo)",
    )
    origen = models.CharField(
        "origen", max_length=30, choices=REPRESENTATIVE_ORIGIN, blank=True,
        help_text="Solo para CONAPRES: MINSA / Gobierno Regional / Asociación de Facultades",
    )
    fecha_inicio = models.DateField("fecha de inicio", null=True, blank=True, help_text="Inicio de participación/cargo")
    fecha_fin = models.DateField("fecha de fin", null=True, blank=True, help_text="Fin de participación/cargo")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "representante"
        verbose_name = "representante"

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Entidades — Universidades
# ---------------------------------------------------------------------------
class University(models.Model):
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la universidad")
    siglas = models.CharField("siglas", max_length=50, blank=True, help_text="Siglas")
    tipo_gestion = models.ForeignKey(
        UniversityManagementType, on_delete=models.PROTECT, db_column="tipo_gestion_id",
        help_text="Pública / privada",
    )
    tipo_entidad = models.ForeignKey(
        UniversityEntityType, on_delete=models.PROTECT, db_column="tipo_entidad_id",
        help_text="Universidad / Escuela posgrado / Escuela superior / Instituto",
    )
    tipo_autorizacion = models.ForeignKey(
        AuthorizationType, on_delete=models.PROTECT, db_column="tipo_autorizacion_id",
        help_text="Licenciada / Denegada / Pendiente",
    )
    codigo_inei = models.CharField("código INEI", max_length=20, blank=True, help_text="Código INEI")
    fecha_constitucion = models.DateField("fecha de constitución", null=True, blank=True, help_text="Fecha de constitución")
    fecha_autorizacion = models.DateField("fecha de autorización", null=True, blank=True, help_text="Fecha de autorización")
    numero_resolucion = models.CharField("número de resolución", max_length=100, blank=True, help_text="Número de resolución")
    direccion_legal = models.CharField("dirección legal", max_length=500, blank=True, help_text="Dirección legal")
    telefono = models.CharField("teléfono", max_length=30, blank=True, help_text="Teléfono")
    correo_institucional = models.CharField("correo institucional", max_length=255, blank=True, help_text="Correo institucional")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    referencia_logo = models.CharField(
        "referencia del logo", max_length=500, blank=True,
        help_text="Referencia externa del logo (repositorio externo)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "universidad"
        verbose_name = "universidad"

    def __str__(self):
        return self.nombre


class UniversityAuthority(models.Model):
    universidad = models.ForeignKey(
        University, on_delete=models.CASCADE, db_column="universidad_id",
        related_name="autoridades", help_text="Universidad",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la autoridad")
    cargo = models.CharField("cargo", max_length=150, help_text="Cargo")
    fecha_inicio_cargo = models.DateField("fecha de inicio del cargo", help_text="Inicio del cargo")
    fecha_fin_cargo = models.DateField("fecha de fin del cargo", null=True, blank=True, help_text="Fin del cargo")
    numero_resolucion = models.CharField("número de resolución", max_length=100, blank=True, help_text="Número de resolución de designación")
    referencia_documento_resolucion = models.CharField(
        "referencia del documento de resolución", max_length=500, blank=True,
        help_text="Referencia externa del PDF de la resolución",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "autoridad_universidad"
        verbose_name = "autoridad de universidad"

    def __str__(self):
        return self.nombre


class Faculty(models.Model):
    universidad = models.ForeignKey(
        University, on_delete=models.CASCADE, db_column="universidad_id",
        related_name="facultades", help_text="Universidad",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la facultad")
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "facultad"
        verbose_name = "facultad"

    def __str__(self):
        return self.nombre


class ProfessionalCareer(models.Model):
    facultad = models.ForeignKey(
        Faculty, on_delete=models.CASCADE, db_column="facultad_id",
        related_name="carreras", help_text="Facultad",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la carrera o programa")
    nivel_academico = models.ForeignKey(
        AcademicLevel, on_delete=models.PROTECT, db_column="nivel_academico_id",
        help_text="Carrera profesional / segunda especialidad / maestría / doctorado",
    )
    especialidad = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, db_column="especialidad_id",
        null=True, blank=True, related_name="+", help_text="Especialidad asociada",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "carrera_profesional"
        verbose_name = "carrera profesional"

    def __str__(self):
        return self.nombre


class UniversityCampus(models.Model):
    universidad = models.ForeignKey(
        University, on_delete=models.CASCADE, db_column="universidad_id",
        related_name="locales", help_text="Universidad",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre del local")
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL, db_column="region_id", null=True, blank=True,
        related_name="+", help_text="Región",
    )
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "local_universidad"
        verbose_name = "local de universidad"

    def __str__(self):
        return self.nombre


# ---------------------------------------------------------------------------
# Seguridad y perfil institucional
# ---------------------------------------------------------------------------
class UserEntityProfile(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column="usuario_id",
        related_name="perfiles_entidad", help_text="Usuario",
    )
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_column="tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad asociada",
    )
    id_objeto = models.PositiveBigIntegerField("id objeto", help_text="Identificador de la entidad asociada")
    entidad = GenericForeignKey("tipo_contenido", "id_objeto")
    grupo = models.ForeignKey(
        "auth.Group", on_delete=models.PROTECT, db_column="grupo_id",
        related_name="+", help_text="Rol institucional",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "perfil_usuario_entidad"
        verbose_name = "perfil de usuario por entidad"
        unique_together = [("usuario", "tipo_contenido", "id_objeto", "grupo")]


# ---------------------------------------------------------------------------
# Núcleo de convenios
# ---------------------------------------------------------------------------
class ConventionTemplate(models.Model):
    tipo_convenio = models.ForeignKey(
        ConventionType, on_delete=models.PROTECT, db_column="tipo_convenio_id",
        help_text="Tipo al que aplica",
    )
    nombre = models.CharField("nombre", max_length=255, help_text="Nombre de la plantilla")
    referencia_externa = models.CharField(
        "referencia externa", max_length=500, help_text="Referencia externa del archivo de plantilla",
    )
    version = models.PositiveIntegerField("versión", default=1, help_text="Versión")
    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "plantilla_convenio"
        verbose_name = "plantilla de convenio"

    def __str__(self):
        return self.nombre


class Convention(models.Model):
    tipo_convenio = models.ForeignKey(
        ConventionType, on_delete=models.PROTECT, db_column="tipo_convenio_id",
        help_text="Marco / Específico",
    )
    convenio_marco = models.ForeignKey(
        "self", on_delete=models.PROTECT, db_column="convenio_marco_id", null=True, blank=True,
        related_name="convenios_especificos",
        help_text="Convenio Marco vigente del que depende el Específico (RN-3)",
    )
    plantilla = models.ForeignKey(
        ConventionTemplate, on_delete=models.SET_NULL, db_column="plantilla_id", null=True, blank=True,
        help_text="Plantilla utilizada",
    )
    codigo = models.CharField("código", max_length=50, blank=True, help_text="Código oficial")
    titulo = models.CharField("título", max_length=255, help_text="Título / denominación")
    solicitante_tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="solicitante_tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad solicitante",
    )
    solicitante_id_objeto = models.PositiveBigIntegerField(
        "id objeto solicitante", help_text="Identificador de la entidad solicitante"
    )
    solicitante = GenericForeignKey("solicitante_tipo_contenido", "solicitante_id_objeto")
    estado_actual = models.ForeignKey(
        ConventionStatus, on_delete=models.PROTECT, db_column="estado_actual_id",
        help_text="Estado actual",
    )
    fecha_solicitud = models.DateField("fecha de solicitud", help_text="Fecha de solicitud")
    fecha_inicio = models.DateField("fecha de inicio", null=True, blank=True, help_text="Inicio de vigencia")
    fecha_fin = models.DateField("fecha de fin", null=True, blank=True, help_text="Fin de vigencia")
    max_campos_clinicos = models.PositiveIntegerField(
        "máximo de campos clínicos", null=True, blank=True,
        help_text="Cantidad máxima de campos clínicos (solo Específico)",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por",
        related_name="+", help_text="Usuario que registró",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        db_table = "convenio"
        verbose_name = "convenio"

    def __str__(self):
        return self.titulo


class ConventionParticipant(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="participantes", help_text="Convenio",
    )
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad participante",
    )
    id_objeto = models.PositiveBigIntegerField("id objeto", help_text="Identificador de la entidad participante")
    entidad = GenericForeignKey("tipo_contenido", "id_objeto")
    tipo_autoridad_firmante = models.ForeignKey(
        SigningAuthorityType, on_delete=models.SET_NULL, db_column="tipo_autoridad_firmante_id",
        null=True, blank=True, help_text="Tipo de autoridad firmante",
    )
    es_firmante = models.BooleanField("es firmante", default=False, help_text="Indica si firma el convenio")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "participante_convenio"
        verbose_name = "participante de convenio"
        unique_together = [("convenio", "tipo_contenido", "id_objeto")]


class ConventionStatusHistory(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="historial_estados", help_text="Convenio",
    )
    estado = models.ForeignKey(
        ConventionStatus, on_delete=models.PROTECT, db_column="estado_id", help_text="Estado registrado",
    )
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="cambiado_por",
        related_name="+", help_text="Responsable del cambio",
    )
    cambiado_en = models.DateTimeField("cambiado en", auto_now_add=True, help_text="Fecha y hora")
    observacion = models.TextField("observación", blank=True, help_text="Observaciones")

    class Meta:
        db_table = "historial_estado_convenio"
        verbose_name = "historial de estado de convenio"


# ---------------------------------------------------------------------------
# Flujo del convenio
# ---------------------------------------------------------------------------
EVALUATION_RESULT = [("VALIDADO", "Validado"), ("OBSERVADO", "Observado"), ("RECHAZADO", "Rechazado")]
OPINION_RESULT = [("FAVORABLE", "Favorable"), ("OBSERVADO", "Observado")]
SIGNATURE_STATUS = [("PENDIENTE", "Pendiente"), ("FIRMADO", "Firmado"), ("DEVUELTO", "Devuelto")]


class TechnicalEvaluation(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="evaluaciones_tecnicas", help_text="Convenio",
    )
    resultado = models.CharField("resultado", max_length=20, choices=EVALUATION_RESULT, help_text="Resultado de la evaluación")
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones")
    subsanacion = models.TextField("subsanación", blank=True, help_text="Subsanación")
    evaluado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="evaluado_por",
        related_name="+", help_text="Responsable",
    )
    organo_minsa = models.ForeignKey(
        MinsaOrgan, on_delete=models.SET_NULL, db_column="organo_minsa_id", null=True, blank=True,
        help_text="Unidad evaluadora (DIGEP)",
    )
    fecha_evaluacion = models.DateField("fecha de evaluación", help_text="Fecha de evaluación")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "evaluacion_tecnica"
        verbose_name = "evaluación técnica"


class ConapresOpinion(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="opiniones_conapres", help_text="Convenio (solo Específico)",
    )
    fecha_solicitud = models.DateField("fecha de solicitud", help_text="Fecha de solicitud de opinión")
    estado_atencion = models.CharField("estado de atención", max_length=20, help_text="Estado de atención")
    resultado_opinion = models.CharField(
        "resultado de la opinión", max_length=20, choices=OPINION_RESULT, blank=True, help_text="Resultado",
    )
    fecha_respuesta = models.DateField("fecha de respuesta", null=True, blank=True, help_text="Fecha de respuesta")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "opinion_conapres"
        verbose_name = "opinión CONAPRES"


class ClinicalField(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="campos_clinicos", help_text="Convenio (solo Específico)",
    )
    ipress = models.ForeignKey(
        Ipress, on_delete=models.PROTECT, db_column="ipress_id", help_text="Sede docente (establecimiento)",
    )
    carrera_profesional = models.ForeignKey(
        ProfessionalCareer, on_delete=models.PROTECT, db_column="carrera_profesional_id",
        help_text="Carrera / programa académico",
    )
    especialidad = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, db_column="especialidad_id", null=True, blank=True,
        related_name="+", help_text="Especialidad",
    )
    cantidad_maxima = models.PositiveIntegerField("cantidad máxima", help_text="Cantidad máxima de campos clínicos autorizados")
    vigencia_inicio = models.DateField("vigencia inicio", help_text="Inicio de vigencia")
    vigencia_fin = models.DateField("vigencia fin", help_text="Fin de vigencia")
    ambito_geografico_sanitario = models.ForeignKey(
        HealthGeographicScope, on_delete=models.PROTECT, db_column="ambito_geografico_sanitario_id",
        help_text="Ámbito",
    )
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "campo_clinico"
        verbose_name = "campo clínico"


class LegalOpinion(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="opiniones_juridicas", help_text="Convenio",
    )
    fecha_envio = models.DateField("fecha de envío", help_text="Fecha de envío a OGAJ")
    resultado_opinion = models.CharField(
        "resultado de la opinión", max_length=20, choices=OPINION_RESULT, blank=True, help_text="Resultado",
    )
    observaciones_legales = models.TextField("observaciones legales", blank=True, help_text="Observaciones legales")
    subsanacion = models.TextField("subsanación", blank=True, help_text="Subsanación")
    fecha_respuesta = models.DateField("fecha de respuesta", null=True, blank=True, help_text="Fecha de respuesta")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "opinion_juridica"
        verbose_name = "opinión jurídica"


class Signature(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="firmas", help_text="Convenio",
    )
    firmante_tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="firmante_tipo_contenido_id",
        related_name="+", help_text="Tipo de entidad firmante",
    )
    firmante_id_objeto = models.PositiveBigIntegerField(
        "id objeto firmante", help_text="Identificador de la entidad firmante"
    )
    firmante = GenericForeignKey("firmante_tipo_contenido", "firmante_id_objeto")
    tipo_autoridad_firmante = models.ForeignKey(
        SigningAuthorityType, on_delete=models.SET_NULL, db_column="tipo_autoridad_firmante_id",
        null=True, blank=True, help_text="Tipo de autoridad firmante",
    )
    orden_firma = models.PositiveSmallIntegerField("orden de firma", null=True, blank=True, help_text="Orden en el circuito")
    fecha_envio = models.DateField("fecha de envío", null=True, blank=True, help_text="Fecha de envío")
    fecha_recepcion = models.DateField("fecha de recepción", null=True, blank=True, help_text="Fecha de recepción")
    estado_firma = models.CharField("estado de firma", max_length=20, choices=SIGNATURE_STATUS, help_text="Estado de firma")
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones o devoluciones")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "firma"
        verbose_name = "firma"


class Publication(models.Model):
    convenio = models.ForeignKey(
        Convention, on_delete=models.CASCADE, db_column="convenio_id",
        related_name="publicaciones", help_text="Convenio",
    )
    fecha_publicacion = models.DateField("fecha de publicación", help_text="Fecha de publicación")
    referencia_publicacion = models.CharField(
        "referencia de publicación", max_length=255, blank=True, help_text="Enlace, código o constancia",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por", related_name="+",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "publicacion"
        verbose_name = "publicación"


# ---------------------------------------------------------------------------
# Documento (adjuntos en repositorio externo) y auditoría
# ---------------------------------------------------------------------------
DOCUMENT_STATUS = [
    ("ACTIVO", "Activo"), ("REEMPLAZADO", "Reemplazado"), ("ANULADO", "Anulado"),
    ("OBSERVADO", "Observado"), ("VALIDADO", "Validado"),
]


class Document(models.Model):
    tipo_documento = models.ForeignKey(
        DocumentType, on_delete=models.PROTECT, db_column="tipo_documento_id", help_text="Tipo de documento",
    )
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, db_column="tipo_contenido_id",
        related_name="+", help_text="Tabla destino",
    )
    id_objeto = models.PositiveBigIntegerField("id objeto", help_text="Registro destino")
    objeto = GenericForeignKey("tipo_contenido", "id_objeto")
    referencia_externa = models.CharField(
        "referencia externa", max_length=500, help_text="Clave/URL del archivo en el repositorio externo",
    )
    nombre_archivo = models.CharField("nombre del archivo", max_length=255, help_text="Nombre del archivo")
    version = models.PositiveIntegerField("versión", default=1, help_text="Versión")
    estado = models.CharField("estado", max_length=20, choices=DOCUMENT_STATUS, default="ACTIVO", help_text="Estado")
    version_anterior = models.ForeignKey(
        "self", on_delete=models.SET_NULL, db_column="version_anterior_id", null=True, blank=True,
        related_name="versiones_siguientes", help_text="Versión previa reemplazada",
    )
    cargado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="cargado_por", related_name="+",
        help_text="Usuario que cargó",
    )
    cargado_en = models.DateTimeField("cargado en", auto_now_add=True, help_text="Fecha y hora de carga")

    class Meta:
        db_table = "documento"
        verbose_name = "documento"


class AuditLog(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, db_column="usuario_id", null=True, blank=True,
        related_name="+", help_text="Usuario que ejecutó la acción",
    )
    accion = models.CharField("acción", max_length=30, help_text="CREAR / ACTUALIZAR / ELIMINAR / CAMBIO_ESTADO / …")
    tipo_contenido = models.ForeignKey(
        ContentType, on_delete=models.PROTECT, db_column="tipo_contenido_id",
        related_name="+", help_text="Entidad afectada",
    )
    id_objeto = models.PositiveBigIntegerField("id objeto", help_text="Registro afectado")
    objeto = GenericForeignKey("tipo_contenido", "id_objeto")
    nombre_campo = models.CharField("nombre del campo", max_length=100, blank=True, help_text="Campo modificado")
    valor_anterior = models.TextField("valor anterior", blank=True, help_text="Valor anterior")
    valor_nuevo = models.TextField("valor nuevo", blank=True, help_text="Valor nuevo")
    direccion_ip = models.CharField("dirección IP", max_length=45, blank=True, help_text="IP de origen")
    creado_en = models.DateTimeField("creado en", auto_now_add=True, help_text="Fecha y hora")

    class Meta:
        db_table = "bitacora_auditoria"
        verbose_name = "bitácora de auditoría"
