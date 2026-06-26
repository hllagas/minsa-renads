"""Modelos del Módulo 3: Registrar Actividades Docente-Asistenciales.

Nombres de clases en inglés; tablas, columnas y descripciones en español.
Reutiliza modelos de los módulos 1 (``convenios``) y 2 (``internados``).
"""

from django.conf import settings
from django.db import models

from apps.convenios.models import Catalog, Ipress
from apps.internados.models import Internship, Intern, Rotation, ServiceArea, Tutor


# ---------------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------------
class ActivityType(Catalog):
    class Meta:
        db_table = "tipo_actividad"
        verbose_name = "tipo de actividad"


class ActivityStatus(Catalog):
    orden = models.PositiveSmallIntegerField("orden", default=0, help_text="Orden en el flujo")

    class Meta:
        db_table = "estado_actividad"
        verbose_name = "estado de actividad"


# ---------------------------------------------------------------------------
# Actividad docente-asistencial
# ---------------------------------------------------------------------------
class TeachingActivity(models.Model):
    interno = models.ForeignKey(
        Intern, on_delete=models.PROTECT, db_column="interno_id", related_name="actividades", help_text="Interno",
    )
    internado = models.ForeignKey(
        Internship, on_delete=models.PROTECT, db_column="internado_id", related_name="actividades", help_text="Internado activo",
    )
    ipress = models.ForeignKey(
        Ipress, on_delete=models.PROTECT, db_column="ipress_id", related_name="actividades", help_text="Sede docente",
    )
    rotacion = models.ForeignKey(
        Rotation, on_delete=models.SET_NULL, db_column="rotacion_id", null=True, blank=True,
        related_name="actividades", help_text="Rotación autorizada asociada (si corresponde)",
    )
    tutor = models.ForeignKey(
        Tutor, on_delete=models.PROTECT, db_column="tutor_id", related_name="actividades", help_text="Tutor / docente responsable",
    )
    servicio_area = models.ForeignKey(
        ServiceArea, on_delete=models.PROTECT, db_column="servicio_area_id", help_text="Servicio, área o unidad",
    )
    tipo_actividad = models.ForeignKey(
        ActivityType, on_delete=models.PROTECT, db_column="tipo_actividad_id", help_text="Tipo de actividad",
    )
    estado_actual = models.ForeignKey(
        ActivityStatus, on_delete=models.PROTECT, db_column="estado_actual_id", help_text="Estado actual",
    )
    fecha_actividad = models.DateField("fecha de actividad", help_text="Fecha de la actividad")
    descripcion = models.TextField("descripción", blank=True, help_text="Descripción o detalle")
    carga_horaria = models.DecimalField(
        "carga horaria", max_digits=5, decimal_places=2, null=True, blank=True, help_text="Horas o carga horaria",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="creado_por", related_name="+",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        db_table = "actividad_docente_asistencial"
        verbose_name = "actividad docente-asistencial"


VALIDATION_RESULT = [("VALIDADA", "Validada"), ("OBSERVADA", "Observada"), ("RECHAZADA", "Rechazada")]


class ActivityValidation(models.Model):
    actividad = models.ForeignKey(
        TeachingActivity, on_delete=models.CASCADE, db_column="actividad_id", related_name="validaciones", help_text="Actividad validada",
    )
    resultado = models.CharField("resultado", max_length=20, choices=VALIDATION_RESULT, help_text="Resultado de la validación")
    comentario = models.TextField("comentario", blank=True, help_text="Comentario de validación")
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="validado_por", related_name="+", help_text="Usuario validador",
    )
    fecha_validacion = models.DateTimeField("fecha de validación", help_text="Fecha y usuario validador")
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        db_table = "validacion_actividad"
        verbose_name = "validación de actividad"


class ActivityStatusHistory(models.Model):
    actividad = models.ForeignKey(
        TeachingActivity, on_delete=models.CASCADE, db_column="actividad_id", related_name="historial_estados", help_text="Actividad",
    )
    estado = models.ForeignKey(
        ActivityStatus, on_delete=models.PROTECT, db_column="estado_id", help_text="Estado registrado",
    )
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="cambiado_por", related_name="+", help_text="Responsable",
    )
    cambiado_en = models.DateTimeField("cambiado en", auto_now_add=True, help_text="Fecha y hora")
    observacion = models.TextField("observación", blank=True, help_text="Observaciones")

    class Meta:
        db_table = "historial_estado_actividad"
        verbose_name = "historial de estado de actividad"
