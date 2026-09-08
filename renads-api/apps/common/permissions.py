"""Permisos base con alcance institucional.

Los módulos extienden estas clases para restringir objetos al ámbito de la
entidad del usuario (`perfil_usuario_entidad`). Ver `docs/arquitectura_desarrollo.md`.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.common.selectors import usuario_pertenece_a_entidad


def exigir_ambito(usuario, tipo_contenido_id: int, id_objeto: str) -> None:
    """Exige que la entidad indicada esté en el ámbito institucional del usuario.

    Exentos: superusuario y rol `Administrador RENADS`. Lanza `PermissionDenied`.
    Útil al crear recursos que pertenecen a una entidad (evita escritura cross-tenant).
    """
    if usuario.is_superuser or usuario.groups.filter(name="Administrador RENADS").exists():
        return
    if not usuario_pertenece_a_entidad(usuario, tipo_contenido_id, id_objeto):
        raise PermissionDenied("La entidad indicada está fuera de tu ámbito institucional.")


class IsSuperUser(BasePermission):
    """Restringe la vista a superusuarios (`is_superuser`).

    Garantiza que solo un superadministrador administre usuarios, roles y
    permisos, evitando la escalación de privilegios (RNF-SEG-01/02/03).
    """

    message = "Solo un superadministrador puede acceder a la gestión de usuarios, roles y permisos."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)


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


class IsModuleEnabled(BasePermission):
    """Gate temporal de escritura por módulo, gobernado por el Calendario.

    Opt-in por atributo de vista `module_content_type = (app_label, model)`:
    - Si la vista no lo declara ⇒ pass-through (nunca bloquea).
    - Solo gatea métodos de escritura; la lectura (`SAFE_METHODS`) queda libre.
    - Exentos: superusuario y rol `Administrador RENADS`.
    - En otro caso, consulta el selector del Calendario (import lazy para evitar
      el ciclo `common` ↔ `calendario`): si el ContentType no tiene una ventana
      vigente, deniega con `codigo="MODULO_FUERA_DE_VENTANA"`.
    """

    def has_permission(self, request, view) -> bool:
        module_ct = getattr(view, "module_content_type", None)
        if module_ct is None:
            return True
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.groups.filter(name="Administrador RENADS").exists():
            return True

        # Import lazy: el selector del Calendario depende de sus modelos; importarlo
        # a nivel de módulo crearía un ciclo con `apps.common`.
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone

        from apps.calendario.selectors import esta_habilitado

        app_label, model = module_ct
        try:
            ct = ContentType.objects.get_by_natural_key(app_label, model)
        except ContentType.DoesNotExist:
            # Si el ContentType no existe, ningún calendario puede gobernarlo.
            return True
        if esta_habilitado(ct.id, now=timezone.now()):
            return True
        raise PermissionDenied(
            detail="El módulo está fuera de su ventana de registro.",
            code="MODULO_FUERA_DE_VENTANA",
        )


class HasEntityScope(BasePermission):
    """Permiso a nivel de objeto: restringe al ámbito de la entidad del usuario.

    La vista debe implementar ``get_entity_reference(obj) -> tuple[int, str] | None``
    devolviendo ``(tipo_contenido_id, id_objeto)`` de la entidad dueña del objeto
    (``id_objeto`` como texto: código RENIPRESS para IPRESS, pk casteado para el resto).
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
