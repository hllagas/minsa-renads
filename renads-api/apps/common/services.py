"""Services transversales: auditoría en bitácora."""

from django.contrib.contenttypes.models import ContentType

from apps.convenios.models import AuditLog


def registrar_auditoria(
    usuario,
    accion: str,
    objeto,
    *,
    nombre_campo: str = "",
    valor_anterior="",
    valor_nuevo="",
    direccion_ip: str | None = None,
) -> AuditLog:
    """Registra una operación crítica en `bitacora_auditoria` (RNF-AUD-01/02)."""
    usuario_valido = usuario if (usuario and getattr(usuario, "is_authenticated", False)) else None
    return AuditLog.objects.create(
        usuario=usuario_valido,
        accion=accion,
        tipo_contenido=ContentType.objects.get_for_model(type(objeto)),
        id_objeto=objeto.pk,
        nombre_campo=nombre_campo,
        valor_anterior="" if valor_anterior is None else str(valor_anterior),
        valor_nuevo="" if valor_nuevo is None else str(valor_nuevo),
        direccion_ip=direccion_ip or "",
    )
