"""Permisos base con alcance institucional.

Los módulos extienden estas clases para restringir objetos al ámbito de la
entidad del usuario (`perfil_usuario_entidad`). Ver `docs/arquitectura_desarrollo.md`.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.common.selectors import usuario_pertenece_a_entidad


def exigir_ambito(usuario, tipo_contenido_id: int, id_objeto: int) -> None:
    """Exige que la entidad indicada esté en el ámbito institucional del usuario.

    Exentos: superusuario y rol `Administrador RENADS`. Lanza `PermissionDenied`.
    Útil al crear recursos que pertenecen a una entidad (evita escritura cross-tenant).
    """
    if usuario.is_superuser or usuario.groups.filter(name="Administrador RENADS").exists():
        return
    if not usuario_pertenece_a_entidad(usuario, tipo_contenido_id, id_objeto):
        raise PermissionDenied("La entidad indicada está fuera de tu ámbito institucional.")


class IsInstitutionalMember(BasePermission):
    """El usuario debe estar autenticado y tener al menos un perfil institucional.

    Los superusuarios pasan siempre.
    """

    message = "El usuario no tiene un perfil institucional activo."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        from apps.common.selectors import perfiles_del_usuario

        return perfiles_del_usuario(user).exists()


class HasEntityScope(BasePermission):
    """Permiso a nivel de objeto: restringe al ámbito de la entidad del usuario.

    La vista debe implementar ``get_entity_reference(obj) -> tuple[int, int] | None``
    devolviendo ``(tipo_contenido_id, id_objeto)`` de la entidad dueña del objeto.
    Si devuelve ``None`` no se aplica restricción. Los superusuarios pasan siempre.
    """

    message = "El objeto está fuera del ámbito institucional del usuario."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_superuser:
            return True
        get_ref = getattr(view, "get_entity_reference", None)
        if get_ref is None:
            return True
        referencia = get_ref(obj)
        if referencia is None:
            return True
        tipo_contenido_id, id_objeto = referencia
        return usuario_pertenece_a_entidad(user, tipo_contenido_id, id_objeto)
