"""Modelos de la feature Calendario de actividades administrativas.

Nombres de clases en inglés; tablas, columnas y descripciones en español.
Una `CalendarActivity` es un hito/ventana de calendario que, opcionalmente
(`controla_acceso=True`), gobierna la escritura de uno o varios módulos
funcionales (referenciados por `ContentType`) durante su ventana de fechas.
"""

from django.conf import settings
from django.db import models


class CalendarActivity(models.Model):
    """Actividad/hito del calendario administrativo.

    Sirve como agenda informativa y, si `controla_acceso=True`, habilita o
    bloquea la escritura de sus `content_types` durante la ventana de fechas
    (`fecha_inicio`..`fecha_fin`). `fecha_fin` NULL = ventana abierta.
    """

    nombre = models.CharField(
        "nombre", max_length=255, help_text="Nombre de la actividad de calendario",
    )
    detalle = models.TextField(
        "detalle", blank=True, help_text="Descripción o detalle de la actividad",
    )
    numero_orden = models.PositiveIntegerField(
        "número de orden",
        default=0,
        help_text="Orden de presentación (no único; usado en el ordenamiento por defecto)",
    )
    fecha_inicio = models.DateField(
        "fecha de inicio", help_text="Fecha de inicio de la ventana",
    )
    fecha_fin = models.DateField(
        "fecha de fin",
        null=True,
        blank=True,
        help_text="Fecha de fin de la ventana. NULL = ventana abierta (sin fecha de cierre)",
    )
    controla_acceso = models.BooleanField(
        "controla acceso",
        default=False,
        help_text="Si es verdadero, la actividad gobierna la escritura de sus content_types",
    )
    activo = models.BooleanField(
        "activo", default=True, help_text="Activación / baja lógica de la actividad",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="creado_por",
        related_name="+",
        null=True,
        blank=True,
        help_text="Usuario que creó la actividad",
    )
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="actualizado_por",
        related_name="+",
        null=True,
        blank=True,
        help_text="Usuario que actualizó la actividad por última vez",
    )
    responsables = models.ManyToManyField(
        "auth.Group",
        db_table="actividad_calendario_responsable",
        blank=True,
        related_name="actividades_calendario_responsable",
        help_text="Roles responsables de la actividad",
    )
    content_types = models.ManyToManyField(
        "contenttypes.ContentType",
        db_table="actividad_calendario_content_type",
        blank=True,
        related_name="+",
        help_text=(
            "Módulos/modelos que la actividad referencia y, si controla_acceso=True, gobierna"
        ),
    )

    class Meta:
        db_table = "actividad_calendario"
        verbose_name = "actividad de calendario"
        verbose_name_plural = "actividades de calendario"
        ordering = ["numero_orden", "id"]

    def __str__(self) -> str:
        return self.nombre
