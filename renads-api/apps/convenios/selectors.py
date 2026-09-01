"""Selectors de lectura del módulo Convenios (incluye alcance institucional)."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import (
    ClinicalFieldAllocation,
    ClinicalFieldRegistration,
    Convention,
    ConventionParticipant,
    ConventionStatusHistory,
    Document,
)


def convenios_visibles(usuario) -> QuerySet[Convention]:
    """Convenios dentro del alcance institucional del usuario.

    Superusuario ve todo. Un usuario ve los convenios donde su entidad es
    solicitante o participante. Sin perfiles institucionales no ve ninguno.
    """
    qs = Convention.objects.select_related(
        "tipo_convenio", "estado_actual", "convenio_marco", "convenio_origen",
        "organo_directorio", "universidad__tipo_entidad",
        "unidad_ejecutora", "facultad",
    ).prefetch_related("adendas__estado_actual")
    if usuario.is_superuser:
        return qs
    refs = entidades_del_usuario(usuario)
    if not refs:
        return qs.none()

    solicitante_q = Q()
    participante_q = Q()
    for tipo_contenido_id, id_objeto in refs:
        solicitante_q |= Q(
            solicitante_tipo_contenido_id=tipo_contenido_id,
            solicitante_id_objeto=id_objeto,
        )
        participante_q |= Q(tipo_contenido_id=tipo_contenido_id, id_objeto=id_objeto)

    convenios_participe = ConventionParticipant.objects.filter(participante_q).values_list(
        "convenio_id", flat=True
    )
    return qs.filter(solicitante_q | Q(id__in=convenios_participe)).distinct()


def historial_convenio(convenio: Convention) -> QuerySet[ConventionStatusHistory]:
    """Historial de estados del convenio, del más antiguo al más reciente."""
    return convenio.historial_estados.select_related("estado", "cambiado_por").order_by(
        "cambiado_en"
    )


def vigencia_efectiva(convenio: Convention):
    """Fecha de fin de vigencia efectiva considerando la cadena de adendas.

    Recorre recursivamente las adendas (`convenio.adendas`) y devuelve la mayor
    `fecha_fin` entre las adendas vigentes de la cadena (estado en
    `ESTADOS_VIGENTES`). Si ninguna adenda está vigente, devuelve `convenio.fecha_fin`.
    Precargar con `prefetch_related("adendas")` en el punto de uso para evitar N+1.
    """
    from apps.convenios.services import ESTADOS_VIGENTES

    mejor = convenio.fecha_fin

    def _recorrer(nodo):
        nonlocal mejor
        for adenda in nodo.adendas.all():
            estado = adenda.estado_actual.codigo if adenda.estado_actual_id else ""
            if estado in ESTADOS_VIGENTES and adenda.fecha_fin is not None:
                if mejor is None or adenda.fecha_fin > mejor:
                    mejor = adenda.fecha_fin
            _recorrer(adenda)

    _recorrer(convenio)
    return mejor


def registros_campo_clinico() -> QuerySet[ClinicalFieldRegistration]:
    """Registros de campos clínicos por sede (a), con FKs precargadas."""
    return ClinicalFieldRegistration.objects.select_related(
        "convenio", "ipress", "carrera_profesional", "especialidad"
    )


def asignaciones_campo_clinico() -> QuerySet[ClinicalFieldAllocation]:
    """Asignaciones de campos clínicos por universidad (b), con FKs precargadas."""
    return ClinicalFieldAllocation.objects.select_related(
        "campo_clinico_ipress", "convenio", "ipress", "carrera_profesional",
        "especialidad", "universidad",
    )


def participantes_de(convenio: Convention) -> QuerySet[ConventionParticipant]:
    return convenio.participantes.select_related("tipo_contenido", "tipo_autoridad_firmante")


def documentos_de(objeto) -> QuerySet[Document]:
    """Documentos asociados a un objeto vía relación genérica."""
    return Document.objects.filter(
        tipo_contenido=ContentType.objects.get_for_model(type(objeto)),
        id_objeto=objeto.pk,
    ).select_related("documento_anexo")
