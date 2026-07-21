"""Services transversales: auditoría en bitácora y gestión documental."""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.convenios.models import AuditLog, Document


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


@transaction.atomic
def adjuntar_documento(
    objeto,
    *,
    tipo_documento,
    nombre_archivo,
    referencia_externa,
    usuario,
    documento_anexo=None,
) -> Document:
    """Adjunta un documento versionado a `objeto` (relación genérica, RNF-DOC-04).

    Versionado: si ya existe un documento `ACTIVO` para el mismo objeto, el nuevo
    documento toma la versión siguiente, enlaza al anterior en `version_anterior`
    y marca al anterior como `REEMPLAZADO`. El **discriminador** de la cadena de
    versiones depende de si se adjunta un anexo:

    - Si `documento_anexo` es `None` (comportamiento por defecto / retrocompatible):
      el activo previo se busca por `(tipo_contenido, id_objeto, tipo_documento)`.
    - Si `documento_anexo` no es `None` (flujo de anexos por actor): el activo
      previo se busca por `(tipo_contenido, id_objeto, documento_anexo)`, de modo
      que cada anexo mantiene su propia cadena de versiones independiente.

    Todo dentro de `transaction.atomic()` y con registro de auditoría. Devuelve la
    nueva instancia `Document` creada.
    """
    tipo_contenido = ContentType.objects.get_for_model(type(objeto))

    # Documento activo previo del mismo objeto. A lo sumo uno; si hubiera varios,
    # se toma el de mayor versión. select_for_update evita carreras. El
    # discriminador es el anexo cuando se adjunta uno, o el tipo de documento en
    # caso contrario (retrocompatible).
    filtros = {
        "tipo_contenido": tipo_contenido,
        "id_objeto": objeto.pk,
        "estado": "ACTIVO",
    }
    if documento_anexo is not None:
        filtros["documento_anexo"] = documento_anexo
    else:
        filtros["tipo_documento"] = tipo_documento

    anterior = (
        Document.objects.select_for_update()
        .filter(**filtros)
        .order_by("-version")
        .first()
    )

    documento = Document.objects.create(
        tipo_documento=tipo_documento,
        tipo_contenido=tipo_contenido,
        id_objeto=objeto.pk,
        referencia_externa=referencia_externa,
        nombre_archivo=nombre_archivo,
        version=(anterior.version + 1) if anterior else 1,
        estado="ACTIVO",
        version_anterior=anterior,
        documento_anexo=documento_anexo,
        cargado_por=usuario,
    )

    registrar_auditoria(usuario, "CREAR", documento)

    if anterior is not None:
        anterior.estado = "REEMPLAZADO"
        anterior.save(update_fields=["estado"])
        registrar_auditoria(
            usuario,
            "CAMBIO_ESTADO",
            anterior,
            nombre_campo="estado",
            valor_anterior="ACTIVO",
            valor_nuevo="REEMPLAZADO",
        )

    return documento
