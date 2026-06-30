"""Selectors de lectura del módulo Convenios (incluye alcance institucional)."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import (
    ClinicalField,
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
        "tipo_convenio", "estado_actual", "convenio_marco",
        "organo_regional__tipo_organo_regional", "universidad__tipo_entidad",
    )
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


def campos_clinicos_de(convenio: Convention) -> QuerySet[ClinicalField]:
    return convenio.campos_clinicos.select_related(
        "ipress", "carrera_profesional", "especialidad", "ambito_geografico_sanitario"
    )


def participantes_de(convenio: Convention) -> QuerySet[ConventionParticipant]:
    return convenio.participantes.select_related("tipo_contenido", "tipo_autoridad_firmante")


def documentos_de(objeto) -> QuerySet[Document]:
    """Documentos asociados a un objeto vía relación genérica."""
    return Document.objects.filter(
        tipo_contenido=ContentType.objects.get_for_model(type(objeto)),
        id_objeto=objeto.pk,
    ).select_related("tipo_documento")
