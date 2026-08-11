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

---

# Validación — T10: Escritura de perfiles institucionales / scope por objeto (`UserEntityProfile`)

**Veredicto: APROBADO (sin errores altos, medios ni bajos).** Se actualiza la guía de pruebas manuales
(`spec/common_usuarios.guia_pruebas.md`) con los casos de T10.

Spec validado: `spec/common_usuarios.md` §T10 (T10.1–T10.4, criterios 1–9, "Endpoints resultantes",
"Verificación de cierre"). Fecha: 2026-08-11.

## Comprobaciones técnicas ejecutadas

| Comando | Resultado |
|---------|-----------|
| `python manage.py check` | `System check identified no issues (0 silenced).` |
| `python manage.py makemigrations --check --dry-run` | `No changes detected` (exit 0) — sin modelos/migraciones nuevos (criterio 8). |
| `python manage.py spectacular --file schema.yml` | `Errors: 0`; warnings preexistentes ajenos a `common`. El path `/api/v1/users/{id}/profiles/` aparece con GET/POST/DELETE; request `UserEntityProfileWrite`, respuesta `UserEntityProfileWriteReadList` (criterio de cierre 3). |

## Cobertura del spec (T10)

| Tarea | Estado | Notas |
|-------|--------|-------|
| **T10.1** `UserEntityProfileWriteSerializer` | OK | `rol`=`PrimaryKeyRelatedField(queryset=Group)` con mensajes en español; `tipo_entidad`=`CharField`; `ids`=`ListField(IntegerField, allow_empty=False)`. `validate_tipo_entidad` resuelve el `ContentType` acotado a `APPS_ENTIDADES_ADMITIDAS=("convenios","internados","actividades")` y lo guarda en `self._content_type`; si no existe → `ValidationError` («El tipo de entidad indicado no es válido.»). `validate` verifica existencia de cada PK vía `content_type.model_class().objects.filter(pk__in=ids)` y lista los faltantes en español; deja `tipo_contenido` en `validated_data`. |
| **T10.2** `UserEntityProfileWriteReadSerializer` | OK | Subclase de `UserEntityProfileSerializer`; reutiliza los 4 campos publicados (`tipo_entidad`/`id_objeto`/`entidad`/`rol`) y añade `id`/`activo` (`read_only`). No modifica `UserEntityProfileSerializer` ni `MeSerializer`. |
| **T10.3** Acción `profiles` en `UserViewSet` | OK | `@action(detail=True, methods=["get","post","delete"], url_path="profiles")`. Import puntual `from apps.convenios.models import UserEntityProfile` dentro de la acción (patrón del selector). GET con `select_related("tipo_contenido","grupo")`, filtra `activo=True` salvo `?incluir_inactivos=true`. POST idempotente dentro de `transaction.atomic()`. DELETE = baja lógica. `get_serializer_class` devuelve `UserEntityProfileWriteSerializer` cuando `action == "profiles"`. |
| **T10.4** OpenAPI / contrato | OK | `@extend_schema(request=..., responses=UserEntityProfileWriteReadSerializer(many=True))`; salida alineada con `docs/api_accesos_frontend.md` §1. |

## Revisión de los puntos de foco

1. **Permisos / anti-escalación (RNF-SEG) — OK.** La acción `profiles` no sobrescribe `permission_classes`; hereda `[IsSuperUser]` del `UserViewSet`. Solo el superadministrador otorga/revoca scope. Sin relajación.
2. **Idempotencia y semántica de estado — OK.** Usa `get_or_create(usuario, tipo_contenido, id_objeto, grupo, defaults={"activo": True})` (no `update_or_create`), coincidiendo con la clave `unique_together (usuario, tipo_contenido, id_objeto, grupo)`. `creado`→`CREAR`; existente inactivo→`activo=False→True`+`ACTIVAR`; existente activo→sin cambio ni auditoría. Reenviar el mismo POST no duplica ni audita. Nota: el texto de "decisión" del spec menciona `update_or_create`, pero **T10.3 y el criterio de aceptación 2/3 exigen distinguir CREAR/ACTIVAR/ya-activo**, lo que requiere `get_or_create`; la implementación es la correcta y no constituye desviación.
3. **DELETE = baja lógica — OK.** `activo=False` + `save(update_fields=["activo"])` (no `delete()`); `400` si falta `profile_id` (query o body); `404` si el perfil no pertenece al usuario (captura también `ValueError`/`TypeError` de un `profile_id` malformado); `204` idempotente si ya estaba inactivo; audita `DESACTIVAR`.
4. **Auditoría (RNF-AUD) — OK.** Cada alta/reactivación/baja llama `registrar_auditoria(request.user, <accion>, perfil)` sobre la instancia `UserEntityProfile`, con `nombre_campo="activo"` y valores anterior/nuevo en reactivación/baja.
5. **Payload genérico y validaciones — OK.** `tipo_entidad` resuelto por `model` acotado a `convenios`/`internados`/`actividades`; `ids` no vacío; existencia por id; `rol` existente; errores en español con `400`.
6. **Consistencia de contrato — OK.** La salida mantiene `tipo_entidad`/`id_objeto`/`entidad`/`rol` (+`id`/`activo`). `UserEntityProfileSerializer` y `MeSerializer` intactos; `/auth/me/` sigue sirviendo exactamente 4 campos.
7. **Cross-app — OK.** Import puntual de `UserEntityProfile` desde `apps.convenios.models` dentro de la acción; sin acoplamiento a serializers/vistas de `convenios`.
8. **Sin migraciones / check / schema — OK.** Ver tabla de comprobaciones técnicas. `runserver` no ejecutado.
9. **Idioma — OK.** Código/endpoints/`url_path` en inglés; docstrings/`help_text`/mensajes en español.

## Genericidad (criterio 9)

El endpoint no tiene ramas por tipo de entidad: `tipo_entidad` se resuelve genéricamente vía `ContentType`.
Funciona con `"ipress"`, `"student"` u otra entidad de las apps admitidas sin cambios de código.

## Notas

- Existe un endpoint independiente `/api/v1/user-entity-profiles/` (CRUD preexistente en `apps/convenios`),
  distinto del sub-recurso `/api/v1/users/{id}/profiles/` de T10. No hay colisión de rutas ni de basenames.
- La observación informativa de atomicidad del bloque T1–T9 queda cubierta en T10: `perform_create`,
  `perform_update`, `destroy`, `set_password` y la acción `profiles` envuelven sus operaciones en
  `transaction.atomic`.

No hay hallazgos de severidad alta, media ni baja. **T10 queda aprobada.**
