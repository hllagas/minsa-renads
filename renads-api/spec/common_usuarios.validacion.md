# Validación — Feature `common`: gestión de usuarios, roles y permisos (superadministrador)

**Veredicto: APROBADO (sin errores altos ni medios).** Se genera la guía de pruebas manuales
(`spec/common_usuarios.guia_pruebas.md`).

Spec validado: `spec/common_usuarios.md` (T1–T9). Revisión con foco de seguridad (escalación de
privilegios). Fecha: 2026-06-29.

## Comprobaciones técnicas ejecutadas

| Comando | Resultado |
|---------|-----------|
| `python manage.py check` | `System check identified no issues (0 silenced).` |
| `python manage.py makemigrations --check --dry-run` | `No changes detected` (exit 0) — sin modelos/migraciones nuevos. |
| `python manage.py spectacular` | 0 errores; 46 warnings preexistentes ajenos a `common` (convenios/internados/actividades). Paths `users`, `groups`, `permissions` y `users/{id}/set-password/` presentes en el esquema. |
| Instanciación de serializers (shell) | Todos instancian sin error; campos esperados presentes. |
| Pruebas funcionales (APIRequestFactory) | 403 no-superusuario, 401 anónimo, rechazo de contraseña débil con mensaje en español, claim `es_superusuario` presente. |

## Cobertura del spec

| Tarea | Estado | Notas |
|-------|--------|-------|
| **T1** Login enriquecido | OK | `get_token` añade claim `es_superusuario` (+`nombre`,`grupos`); `validate` añade `es_superusuario`/`nombre`/`grupos` al body sin romper el flujo JWT. Verificado: claim presente. |
| **T2** `IsSuperUser` | OK | `has_permission` exige `is_authenticated and is_superuser`; `message` en español. Sin `has_object_permission` (alcance global). |
| **T3.1** `UserReadSerializer` | OK | No incluye `password`; `read_only_fields=fields`; `groups` (PK) + `groups_detalle` (`{id,name}`). Verificado: hash no se filtra en la salida. |
| **T3.2** `UserCreateSerializer` | OK | `password` write_only/required; `validate_password` aplica validadores Django; `email` único (`UniqueValidator`, mensaje español); `create` usa `set_password` y `groups.set(...)` tras `save()`. |
| **T3.3** `UserUpdateSerializer` | OK | Sin `password`; `email` único excluyendo instancia (lo maneja `UniqueValidator` con `instance`); `update` asigna escalares y `groups.set(...)` solo si viene `groups`. |
| **T3.4** `SetPasswordSerializer` | OK | Campo único `password` write_only con `validate_password`. |
| **T4.1** `GroupSerializer` | OK | `permissions` por PK + `permissions_detalle`; `create`/`update` con `permissions.set(...)`. |
| **T4.2** `PermissionSerializer` | OK | Todo `read_only`; expone `app_label`/`model` del `content_type`. |
| **T5** `UserViewSet` | OK | `IsSuperUser`; `get_serializer_class` correcto por acción; filtros/búsqueda/orden; `perform_create`/`perform_update` auditan; `destroy`=`is_active=False`+`DESACTIVAR`; action `set-password`. |
| **T6** `GroupViewSet` | OK | `IsSuperUser`; auditoría CREAR/ACTUALIZAR; `perform_destroy` audita `ELIMINAR` y luego `delete()`. |
| **T7** `PermissionViewSet` | OK | `ReadOnlyModelViewSet`; `IsSuperUser`; filtros por `content_type`/`content_type__app_label`. |
| **T8** Router `apps/common/urls.py` | OK | `DefaultRouter` con basenames `user`/`group`/`permission`. |
| **T9** Montaje en `config/api_urls.py` | OK | `path("", include("apps.common.urls"))`; sin colisión de basenames; `reverse()` resuelve las rutas bajo `/api/v1/`. |

## Revisión de seguridad (puntos solicitados)

1. **Permiso en todos los endpoints — OK.** `UserViewSet`, `GroupViewSet`, `PermissionViewSet` declaran
   `permission_classes = [IsSuperUser]`. La action `set-password` hereda el permiso del ViewSet (no lo
   sobrescribe). Verificado en runtime: no-superusuario→403 en `list` y en `set-password`; anónimo→401.
   No hay viewset/action sin el permiso.
2. **Contraseña nunca expuesta — OK.** `password` es `write_only` en create y set-password; ausente de
   `UserReadSerializer`. Verificado: la salida de `UserReadSerializer` no contiene `password` ni el hash
   (`pbkdf2`/`argon`). `set_password` se usa en create (serializer) y en la action; nunca se guarda en
   claro ni se pasa al constructor del modelo. `validate_password` se aplica en create y en set-password
   (rechazo de débil → 400 con mensajes en español).
3. **`destroy` = desactivación — OK.** `UserViewSet.destroy` hace `is_active=False` +
   `save(update_fields=["is_active"])`, no `delete()`. Audita `DESACTIVAR` con
   `valor_anterior=True/valor_nuevo=False`. Devuelve 204.
4. **Login JWT — OK.** Claim y body enriquecidos sin alterar `access`/`refresh` (se llama a
   `super().validate`/`super().get_token`). Claim `es_superusuario` confirmado en token decodificado.
5. **Auditoría sin duplicación — OK.** Cada operación llama `registrar_auditoria` exactamente una vez:
   create→CREAR, update→ACTUALIZAR (incluye cambios de `groups`/flags), destroy→DESACTIVAR,
   set-password→ACTUALIZAR (`nombre_campo="password"`, sin registrar el valor), grupos→CREAR/ACTUALIZAR/
   ELIMINAR. No se usa ningún mixin que registre una segunda vez. `accion` es `CharField` sin `choices`,
   por lo que `DESACTIVAR`/`ELIMINAR` se aceptan.
6. **Asignación M2M `groups` — OK (con nota informativa).** Orden correcto: `User(...).save()` y luego
   `groups.set(...)` (la M2M requiere PK). En update, `groups.set(...)` solo si viene `groups`.
7. **Sin dependencia inversa — OK.** Los archivos nuevos/editados (`serializers.py`, `views.py`,
   `permissions.py`, `urls.py`) no importan de `apps.convenios`. La dependencia hacia
   `apps.convenios.models` (AuditLog/Document/UserEntityProfile) es preexistente y aislada en
   `services.py`/`selectors.py`, tal como autoriza el spec (reutilizar `registrar_auditoria`).
8. **Convenciones CLAUDE.md — OK.** Clases/funciones/endpoints/basenames en inglés; docstrings,
   `help_text`, `message` y mensajes de error al usuario en español. Serializers instancian sin error.

## Hallazgos

| # | Severidad | Ubicación | Hallazgo | Sugerencia |
|---|-----------|-----------|----------|------------|
| 1 | Informativo (no bloqueante) | `apps/common/serializers.py:162` (`UserCreateSerializer.create`), `:235` (`GroupSerializer.create`), `apps/common/views.py:62/66/107/111` | El alta/edición ejecuta `save()` + `set(...)` M2M (y el ViewSet añade `registrar_auditoria`) sin envoltura `transaction.atomic`. `ATOMIC_REQUESTS` no está activo en dev/prod. El orden es correcto; el riesgo es solo robustez: si la asignación M2M o la auditoría fallara tras crear el usuario/grupo, quedaría un registro parcial. No es requisito del spec y no implica escalación de privilegios (un fallo dejaría *menos* privilegios, no más). | Opcional: envolver `perform_create`/`perform_update`/`set_password`/`destroy` (o los `create`/`update` de los serializers) en `transaction.atomic()` para atomicidad completa. |

No hay hallazgos de severidad alta ni media. La feature queda **aprobada**.
