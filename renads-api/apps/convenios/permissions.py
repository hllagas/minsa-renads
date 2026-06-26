"""Permisos del módulo Convenios: alcance institucional y verificación de rol."""

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import ConventionParticipant

ROL_ADMIN = "Administrador RENADS"


def _es_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or user.groups.filter(name=ROL_ADMIN).exists()))


class IsAdminRole(BasePermission):
    """Solo superusuario o rol `Administrador RENADS`."""

    message = "Requiere el rol Administrador RENADS."

    def has_permission(self, request, view) -> bool:
        return _es_admin(request.user)


class IsAdminRoleOrReadOnly(BasePermission):
    """Lectura para autenticados; escritura solo superusuario o `Administrador RENADS`."""

    message = "La escritura requiere el rol Administrador RENADS."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _es_admin(user)


class ConventionScope(BasePermission):
    """Alcance institucional a nivel de objeto sobre `Convention`.

    Permite el acceso si la entidad del usuario es **solicitante** o
    **participante** del convenio (coherente con `selectors.convenios_visibles`).
    Los superusuarios pasan siempre.
    """

    message = "El convenio está fuera del ámbito institucional del usuario."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_superuser:
            return True
        refs = entidades_del_usuario(user)
        if not refs:
            return False
        if (obj.solicitante_tipo_contenido_id, obj.solicitante_id_objeto) in refs:
            return True
        condicion = Q()
        for tipo_contenido_id, id_objeto in refs:
            condicion |= Q(tipo_contenido_id=tipo_contenido_id, id_objeto=id_objeto)
        return ConventionParticipant.objects.filter(condicion, convenio=obj).exists()


def exigir_roles(request, *roles: str) -> None:
    """Exige que el usuario pertenezca a alguno de los roles indicados.

    Los superusuarios pasan siempre. Lanza ``PermissionDenied`` si no cumple.
    """
    user = request.user
    if user.is_superuser:
        return
    if not user.groups.filter(name__in=roles).exists():
        raise PermissionDenied(f"Requiere uno de los roles: {', '.join(roles)}.")
