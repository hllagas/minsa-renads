"""Modelos del Módulo 2: Registrar Internados.

Nombres de clases en inglés; tablas, columnas y descripciones en español.
Reutiliza modelos del módulo 1 (app ``convenios``).
"""

from django.conf import settings
from django.db import models

from apps.convenios.models import (
    Catalog,
    Convention,
    ClinicalField,
    ConventionParticipant,
    HealthGeographicScope,
    Ipress,
    ProfessionalCareer,
    Specialty,
    Ubigeo,
    University,
)


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------
class InternshipStatus(Catalog):
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Orden en el flujo")

    class Meta:
        db_table = "estado_internado"
        verbose_name = "estado de internado"


class RotationStatus(Catalog):
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Orden en el flujo")

    class Meta:
        db_table = "estado_rotacion"
        verbose_name = "estado de rotación"


class ServiceArea(Catalog):
    class Meta:
        db_table = "servicio_area"
        verbose_name = "servicio, área o unidad"


class IdentityDocumentType(Catalog):
    class Meta:
        db_table = "tipo_documento_identidad"
        verbose_name = "tipo de documento de identidad"


# ---------------------------------------------------------------------------
# Interno y tutor
# ---------------------------------------------------------------------------
SEX = [("M", "Masculino"), ("F", "Femenino")]


class Intern(models.Model):
    tipo_documento_identidad = models.ForeignKey(
        IdentityDocumentType, on_delete=models.PROTECT, db_column="tipo_documento_identidad_id",
        related_name="+", help_text="Tipo de documento",
    )
    numero_documento = models.CharField("número de documento", max_length=20, help_text="Número de documento de identidad")
    nombres = models.CharField("nombres", max_length=150, help_text="Nombres")
    apellido_paterno = models.CharField("apellido paterno", max_length=100, help_text="Apellido paterno")
    apellido_materno = models.CharField("apellido materno", max_length=100, blank=True, help_text="Apellido materno")
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True, help_text="Fecha de nacimiento")
    sexo = models.CharField("sexo", max_length=1, choices=SEX, blank=True, help_text="M / F")
    correo = models.CharField("correo", max_length=255, blank=True, help_text="Correo electrónico")
    telefono = models.CharField("teléfono", max_length=30, blank=True, help_text="Teléfono")
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    universidad = models.ForeignKey(
        University, on_delete=models.PROTECT, db_column="universidad_id",
        related_name="internos", help_text="Universidad de procedencia",
    )
    carrera_profesional = models.ForeignKey(
        ProfessionalCareer, on_delete=models.PROTECT, db_column="carrera_profesional_id",
        related_name="+", help_text="Carrera / programa",
    )
    especialidad = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, db_column="especialidad_id", null=True, blank=True,
        related_name="+", help_text="Especialidad (segunda especialidad)",
    )
    codigo_universitario = models.CharField("código universitario", max_length=50, blank=True, help_text="Código universitario / matrícula")
    anio_academico = models.PositiveSmallIntegerField("año académico", null=True, blank=True, help_text="Año académico")
    activo = models.BooleanField("activo", default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por", related_name="+",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "interno"
        verbose_name = "interno"
        unique_together = [("tipo_documento_identidad", "numero_documento")]

    def __str__(self):
        return f"{self.apellido_paterno} {self.nombres}"


class Tutor(models.Model):
    tipo_documento_identidad = models.ForeignKey(
        IdentityDocumentType, on_delete=models.PROTECT, db_column="tipo_documento_identidad_id",
        related_name="+", help_text="Tipo de documento",
    )
    numero_documento = models.CharField("número de documento", max_length=20, help_text="Número de documento de identidad")
    nombres = models.CharField("nombres", max_length=150, help_text="Nombres")
    apellido_paterno = models.CharField("apellido paterno", max_length=100, help_text="Apellido paterno")
    apellido_materno = models.CharField("apellido materno", max_length=100, blank=True, help_text="Apellido materno")
    correo = models.CharField("correo", max_length=255, blank=True, help_text="Correo electrónico")
    telefono = models.CharField("teléfono", max_length=30, blank=True, help_text="Teléfono")
    numero_colegiatura = models.CharField("número de colegiatura", max_length=50, blank=True, help_text="Número de colegiatura")
    direccion = models.CharField("dirección", max_length=500, blank=True, help_text="Dirección")
    ubigeo = models.ForeignKey(
        Ubigeo, on_delete=models.PROTECT, db_column="ubigeo_id", null=True, blank=True,
        related_name="+", help_text="Ubicación geográfica (UBIGEO)",
    )
    especialidad = models.ForeignKey(
        Specialty, on_delete=models.SET_NULL, db_column="especialidad_id", null=True, blank=True,
        related_name="+", help_text="Especialidad del tutor",
    )
    ipress = models.ForeignKey(
        Ipress, on_delete=models.SET_NULL, db_column="ipress_id", null=True, blank=True,
        related_name="tutores", help_text="Establecimiento al que pertenece",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        db_table = "tutor"
        verbose_name = "tutor"

    def __str__(self):
        return f"{self.apellido_paterno} {self.nombres}"


# ---------------------------------------------------------------------------
# Internado
# ---------------------------------------------------------------------------
class Internship(models.Model):
    interno = models.ForeignKey(
        Intern, on_delete=models.PROTECT, db_column="interno_id", related_name="internados", help_text="Interno",
    )
    convenio = models.ForeignKey(
        Convention, on_delete=models.PROTECT, db_column="convenio_id", related_name="internados",
        help_text="Convenio Específico vigente que lo respalda",
    )
    campo_clinico = models.ForeignKey(
        ClinicalField, on_delete=models.PROTECT, db_column="campo_clinico_id", related_name="internados",
        help_text="Campo clínico autorizado asignado",
    )
    ipress = models.ForeignKey(
        Ipress, on_delete=models.PROTECT, db_column="ipress_id", related_name="internados_principales",
        help_text="Sede docente principal",
    )
    tutor = models.ForeignKey(
        Tutor, on_delete=models.PROTECT, db_column="tutor_id", related_name="internados", help_text="Tutor responsable actual",
    )
    ambito_geografico_sanitario = models.ForeignKey(
        HealthGeographicScope, on_delete=models.PROTECT, db_column="ambito_geografico_sanitario_id",
        related_name="+", help_text="Ámbito geográfico sanitario",
    )
    estado_actual = models.ForeignKey(
        InternshipStatus, on_delete=models.PROTECT, db_column="estado_actual_id", help_text="Estado actual",
    )
    fecha_inicio = models.DateField("fecha de inicio", help_text="Fecha de inicio")
    fecha_fin = models.DateField("fecha de fin", help_text="Fecha de fin (máx. 1 año)")
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por", related_name="+",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        db_table = "internado"
        verbose_name = "internado"


class InternshipStatusHistory(models.Model):
    internado = models.ForeignKey(
        Internship, on_delete=models.CASCADE, db_column="internado_id", related_name="historial_estados", help_text="Internado",
    )
    estado = models.ForeignKey(
        InternshipStatus, on_delete=models.PROTECT, db_column="estado_id", help_text="Estado registrado",
    )
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="cambiado_por", related_name="+", help_text="Responsable",
    )
    cambiado_en = models.DateTimeField("cambiado en", auto_now_add=True, help_text="Fecha y hora")
    observacion = models.TextField("observación", blank=True, help_text="Observaciones")

    class Meta:
        db_table = "historial_estado_internado"
        verbose_name = "historial de estado de internado"


class TutorHistory(models.Model):
    internado = models.ForeignKey(
        Internship, on_delete=models.CASCADE, db_column="internado_id", related_name="historial_tutores", help_text="Internado",
    )
    tutor = models.ForeignKey(
        Tutor, on_delete=models.PROTECT, db_column="tutor_id", related_name="+", help_text="Tutor asignado en este registro",
    )
    fecha_cambio = models.DateField("fecha de cambio", help_text="Fecha del cambio")
    motivo = models.TextField("motivo", help_text="Motivo del cambio")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="responsable_id", related_name="+", help_text="Responsable del cambio",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "historial_tutor"
        verbose_name = "historial de tutor"


# ---------------------------------------------------------------------------
# Rotaciones
# ---------------------------------------------------------------------------
AUTHORIZATION_RESULT = [("APROBADO", "Aprobado"), ("OBSERVADO", "Observado"), ("RECHAZADO", "Rechazado")]


class Rotation(models.Model):
    internado = models.ForeignKey(
        Internship, on_delete=models.CASCADE, db_column="internado_id", related_name="rotaciones", help_text="Internado",
    )
    numero_rotacion = models.PositiveSmallIntegerField("número de rotación", help_text="Número de rotación (1–4, RN-9)")
    ipress_origen = models.ForeignKey(
        Ipress, on_delete=models.PROTECT, db_column="ipress_origen_id", related_name="+", help_text="Sede de origen",
    )
    ipress_destino = models.ForeignKey(
        Ipress, on_delete=models.PROTECT, db_column="ipress_destino_id", related_name="+", help_text="Sede de destino",
    )
    servicio_area = models.ForeignKey(
        ServiceArea, on_delete=models.PROTECT, db_column="servicio_area_id", help_text="Servicio, área o unidad",
    )
    estado_actual = models.ForeignKey(
        RotationStatus, on_delete=models.PROTECT, db_column="estado_actual_id", help_text="Estado actual",
    )
    fecha_inicio = models.DateField("fecha de inicio", help_text="Inicio de la rotación")
    fecha_fin = models.DateField("fecha de fin", help_text="Fin de la rotación")
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por", related_name="+",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "rotacion"
        verbose_name = "rotación"


class RotationAuthorization(models.Model):
    rotacion = models.ForeignKey(
        Rotation, on_delete=models.CASCADE, db_column="rotacion_id", related_name="autorizaciones", help_text="Rotación",
    )
    participante_convenio = models.ForeignKey(
        ConventionParticipant, on_delete=models.PROTECT, db_column="participante_convenio_id",
        related_name="autorizaciones_rotacion",
        help_text="Autoridad suscrita en el Convenio Específico que autoriza",
    )
    resultado = models.CharField("resultado", max_length=20, choices=AUTHORIZATION_RESULT, help_text="Resultado")
    fecha_autorizacion = models.DateField("fecha de autorización", help_text="Fecha de autorización")
    observaciones = models.TextField("observaciones", blank=True, help_text="Observaciones")
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="autorizado_por", related_name="+",
        help_text="Usuario que registra la autorización",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "autorizacion_rotacion"
        verbose_name = "autorización de rotación"


class RotationStatusHistory(models.Model):
    rotacion = models.ForeignKey(
        Rotation, on_delete=models.CASCADE, db_column="rotacion_id", related_name="historial_estados", help_text="Rotación",
    )
    estado = models.ForeignKey(
        RotationStatus, on_delete=models.PROTECT, db_column="estado_id", help_text="Estado registrado",
    )
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="cambiado_por", related_name="+", help_text="Responsable",
    )
    cambiado_en = models.DateTimeField("cambiado en", auto_now_add=True, help_text="Fecha y hora")
    observacion = models.TextField("observación", blank=True, help_text="Observaciones")

    class Meta:
        db_table = "historial_estado_rotacion"
        verbose_name = "historial de estado de rotación"
