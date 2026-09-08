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


def entidades_del_usuario(usuario: AbstractBaseUser) -> list[tuple[int, str]]:
    """Pares (tipo_contenido_id, id_objeto) de las entidades a las que pertenece el usuario.

    El ``id_objeto`` es ``CharField`` (texto): para IPRESS es el código RENIPRESS; para el
    resto de entidades es el pk entero casteado a ``str``. El cast explícito blinda la
    comparación por ``str`` en permisos y selectores.
    """
    return [
        (tc, str(oid))
        for tc, oid in perfiles_del_usuario(usuario).values_list("tipo_contenido_id", "id_objeto")
    ]


def usuario_pertenece_a_entidad(usuario: AbstractBaseUser, tipo_contenido_id: int, id_objeto: str) -> bool:
    """Indica si el usuario tiene un perfil activo en la entidad indicada (comparación por str)."""
    return perfiles_del_usuario(usuario).filter(
        tipo_contenido_id=tipo_contenido_id, id_objeto=str(id_objeto)
    ).exists()
