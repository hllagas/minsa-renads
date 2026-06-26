"""Permisos del módulo Actividades: alcance institucional por universidad del interno o sede."""

from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import BasePermission

from apps.common.selectors import entidades_del_usuario
from apps.convenios.models import Ipress, University


class ActivityScope(BasePermission):
    """Acceso a nivel de objeto: universidad del interno o sede (IPRESS) en el ámbito del usuario."""

    message = "La actividad está fuera del ámbito institucional del usuario."

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if user.is_superuser:
            return True
        refs = entidades_del_usuario(user)
        if not refs:
            return False
        ct_uni = ContentType.objects.get_for_model(University).id
        ct_ip = ContentType.objects.get_for_model(Ipress).id
        return (ct_uni, obj.interno.universidad_id) in refs or (ct_ip, obj.ipress_id) in refs
