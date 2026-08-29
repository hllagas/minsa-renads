"""Services de la feature Calendario: escritura con auditoría (fuente única).

La escritura del CRUD delega aquí para fijar `creado_por`/`actualizado_por` y
registrar la auditoría (`bitacora_auditoria`), evitando la doble auditoría del
`AuditedModelViewSet` (mismo patrón que `ClinicalField*ViewSet`).
"""

from django.db import transaction

from apps.calendario.models import CalendarActivity
from apps.common.services import registrar_auditoria


@transaction.atomic
def crear_actividad_calendario(*, datos: dict, usuario) -> CalendarActivity:
    """Crea una actividad de calendario, fija auditoría de creación y registra bitácora."""
    content_types = datos.pop("content_types", None)
    actividad = CalendarActivity(**datos)
    actividad.creado_por = usuario
    actividad.actualizado_por = usuario
    actividad.save()
    if content_types is not None:
        actividad.content_types.set(content_types)
    registrar_auditoria(usuario, "CREAR", actividad)
    return actividad


@transaction.atomic
def actualizar_actividad_calendario(
    *, actividad: CalendarActivity, datos: dict, usuario
) -> CalendarActivity:
    """Actualiza una actividad de calendario, fija auditoría y registra bitácora."""
    content_types = datos.pop("content_types", None)
    for campo, valor in datos.items():
        setattr(actividad, campo, valor)
    actividad.actualizado_por = usuario
    actividad.save()
    if content_types is not None:
        actividad.content_types.set(content_types)
    registrar_auditoria(usuario, "ACTUALIZAR", actividad)
    return actividad
