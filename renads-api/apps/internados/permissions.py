"""Permisos del módulo Internados: alcance institucional por universidad del interno."""

from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import Ipress, University
from apps.internados.models import Internship

ROLES_ESCRITURA_PERSONAS = ("Universidad", "Administrador RENADS")


class IsUniversityOrReadOnly(BasePermission):
    """Lectura para autenticados; escritura solo `Universidad` o `Administrador RENADS`."""

    message = "La escritura requiere el rol Universidad o Administrador RENADS."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_superuser or user.groups.filter(name__in=ROLES_ESCRITURA_PERSONAS).exists()


class InternshipScope(BasePermission):
    """Alcance a nivel de objeto: la universidad del interno debe estar en el ámbito del usuario.

    Aplica tanto a `Internship` como a `Rotation` (resuelve el internado). Superusuario pasa.
    """

    message = "El internado/rotación está fuera del ámbito institucional del usuario."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_superuser:
            return True
        internado = obj if isinstance(obj, Internship) else obj.internado
        refs = entidades_del_usuario(user)
        if not refs:
            return False
        ct_uni = ContentType.objects.get_for_model(University).id
        ct_ip = ContentType.objects.get_for_model(Ipress).id
        return (ct_uni, internado.interno.universidad_id) in refs or (ct_ip, internado.ipress_id) in refs
