"""Selectors transversales de usuarios y alcance institucional."""

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet

from apps.convenios.models import UserEntityProfile


def grupos_del_usuario(usuario: AbstractBaseUser) -> list[str]:
    """Nombres de los grupos (roles) del usuario."""
    return list(usuario.groups.values_list("name", flat=True))


def perfiles_del_usuario(usuario: AbstractBaseUser) -> QuerySet[UserEntityProfile]:
    """Perfiles institucionales activos del usuario (entidad + rol)."""
    return (
        UserEntityProfile.objects.filter(usuario=usuario, activo=True)
        .select_related("tipo_contenido", "grupo")
    )


def entidades_del_usuario(usuario: AbstractBaseUser) -> list[tuple[int, int]]:
    """Pares (tipo_contenido_id, id_objeto) de las entidades a las que pertenece el usuario."""
    return list(
        perfiles_del_usuario(usuario).values_list("tipo_contenido_id", "id_objeto")
    )


def usuario_pertenece_a_entidad(usuario: AbstractBaseUser, tipo_contenido_id: int, id_objeto: int) -> bool:
    """Indica si el usuario tiene un perfil activo en la entidad indicada."""
    return perfiles_del_usuario(usuario).filter(
        tipo_contenido_id=tipo_contenido_id, id_objeto=id_objeto
    ).exists()
