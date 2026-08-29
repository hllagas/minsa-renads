# Spec — Feature transversal `common`: gestión de usuarios, roles y permisos (solo superadministrador)

Lista de tareas exactas para incorporar la **administración de usuarios, grupos (roles) y permisos**
al sistema, restringida a **superusuario** (`is_superuser`), dentro de la app-librería
`apps/common`. Producido por el agente **spec** (SDD). El agente **implement** ejecuta estas tareas en
orden; el **validator** revisa contra este documento y genera `spec/common_usuarios.validacion.md`.

> Feature **aditiva** y transversal. **No tocar** los specs de módulo ya cerrados (`convenios`,
> `internados`, `actividades`) ni sus CRUD. No crea modelos nuevos: usa los modelos nativos de Django
> `User`, `Group`, `Permission`.

## Resumen

`apps/common` es una **app-librería** (no está en `INSTALLED_APPS`, sin modelos propios); sus
serializers/views/urls funcionan igual que los de una app de módulo. La autenticación JWT y el endpoint
`auth/me/` ya existen. Esta feature añade:

- **Auth enriquecido:** el login (`POST /auth/token/`) debe exponer `es_superusuario` tanto en los
  **claims del JWT** como en el **body de la respuesta**, para que el frontend habilite/oculte la UI de
  administración.
- **Permiso `IsSuperUser`:** nuevo permiso que restringe todo el conjunto de administración a
  superusuarios (evita escalación de privilegios: solo un superadmin crea usuarios o concede
  `is_superuser`/grupos).
- **CRUD de usuarios:** sobre `django.contrib.auth.models.User`, con `destroy` = **desactivación**
  (`is_active = False`), nunca borrado físico (conserva trazabilidad y FKs `PROTECT` de
  auditoría/`cargado_por`). Acción dedicada para cambiar contraseña.
- **CRUD de grupos (roles):** sobre `Group`, incluyendo asignación de permisos al grupo.
- **Catálogo de permisos (solo lectura):** sobre `Permission`, para alimentar la UI.
- **Escritura de scope por objeto (`UserEntityProfile`, T10):** otorgar/revocar a un usuario el acceso a
  una o varias entidades institucionales (universidades, IPRESS, etc.) bajo un rol — sub-recurso de
  usuarios.
- **Lookup de tipos de entidad asignables (T11):** endpoint de solo lectura que lista los tipos de
  entidad elegibles para asignar un perfil (alimenta el selector del alta de perfiles del frontend y
  comparte allowlist con la validación de T10).

**Entidades cubiertas:** `User` (tabla `auth_user`), `Group` (`auth_group`), `Permission`
(`auth_permission`), más las M2M `auth_user_groups` y `auth_group_permissions`, y **`UserEntityProfile`**
(tabla `perfil_usuario_entidad`, definida en `apps/convenios/models.py:490` — schema en
`docs/db_schema_modulo_01_convenios.md` §7).

**Convenciones (CLAUDE.md):** clases/funciones/endpoints/`basename` en inglés; docstrings, comentarios,
`help_text` y mensajes de error al usuario en español. ViewSets delgados. Auditoría explícita en cada
operación de escritura (RNF-AUD-01/02). Contraseñas siempre `write_only` + `set_password` +
`validate_password`; nunca exponer el hash en lecturas.

**Restricciones de alcance:**
- **No** crear modelos ni migraciones nuevas (`makemigrations` debe salir vacío).
- **No** crear archivos de tests automatizados (verificación por `/code-review` + guía manual, regla MVP).
- **No** crear endpoint de login nuevo: se **enriquece** el existente.
- Reutilizar `registrar_auditoria` (`apps/common/services.py:9`) para la bitácora.

---

## T1 — Enriquecer el login con `es_superusuario` (`apps/common/serializers.py` — EDITAR)

Modificar `CustomTokenObtainPairSerializer` (no crear serializer ni vista nuevos):

- **T1.1** En `get_token(cls, user)`, además de los claims actuales (`nombre`, `grupos`), añadir:
  `token["es_superusuario"] = user.is_superuser`.
- **T1.2** Sobrescribir `validate(self, attrs)` para enriquecer el **body** de la respuesta de
  `POST /auth/token/`:
  ```python
  def validate(self, attrs):
      data = super().validate(attrs)  # access + refresh
      data["es_superusuario"] = self.user.is_superuser
      data["nombre"] = self.user.get_full_name() or self.user.get_username()
      data["grupos"] = list(self.user.groups.values_list("name", flat=True))
      return data
  ```
  (`self.user` queda disponible tras `super().validate()`.)
- **T1.3** Mantener `CustomTokenObtainPairView` y la ruta `auth/token/` sin cambios (siguen usando este
  serializer).

**Reglas:** sin lógica de negocio adicional; solo exposición de datos de identidad ya existentes.

**Criterio de aceptación:** `POST /auth/token/` devuelve `access`, `refresh`, `es_superusuario`
(bool), `nombre` y `grupos`; el JWT decodificado incluye el claim `es_superusuario`. El frontend lo usa
para habilitar la UI de administración (documentar en docstring).

---

## T2 — Permiso `IsSuperUser` (`apps/common/permissions.py` — EDITAR)

Añadir al archivo existente:

- **T2.1** `IsSuperUser(BasePermission)` con `message` en español (p. ej. «Solo un superadministrador
  puede acceder a la gestión de usuarios, roles y permisos.») y:
  ```python
  def has_permission(self, request, view) -> bool:
      user = request.user
      return bool(user and user.is_authenticated and user.is_superuser)
  ```
- **T2.2** No requiere `has_object_permission` (el alcance es global: superusuario o nada).

**Criterio de aceptación:** un usuario no autenticado o sin `is_superuser` recibe `403` en cualquier
vista que use este permiso; un superusuario pasa siempre.

---

## T3 — Serializers de usuario (`apps/common/serializers.py` — EDITAR)

Importar al inicio: `from django.contrib.auth.models import User, Group, Permission`,
`from django.contrib.auth.password_validation import validate_password`,
`from django.contrib.contenttypes.models import ContentType` (si se requiere para `Permission`).

### T3.1 — `UserReadSerializer` (lectura)

`ModelSerializer` sobre `User`. Expone exactamente: `id`, `username`, `email`, `first_name`,
`last_name`, `is_active`, `is_staff`, `is_superuser`, `date_joined`, `last_login`, y `groups` como:
- `groups` → ids (PK) de los grupos; **y** un campo auxiliar read-only `groups_detalle`
  (`SerializerMethodField` o `GroupSerializer(many=True, read_only=True)` reducido) que liste
  `{id, name}` para que la UI muestre nombres legibles.

**No** incluir `password`. `date_joined`, `last_login`, `is_superuser`/`is_staff`/`is_active`,
`groups`, `id` quedan `read_only` en este serializer de lectura.

### T3.2 — `UserCreateSerializer` (escritura — alta)

`ModelSerializer` sobre `User`. Campos: `username`, `email`, `first_name`, `last_name`, `password`
(`write_only=True`, `required=True`), `is_active`, `is_staff`, `is_superuser`, `groups`
(`PrimaryKeyRelatedField(many=True, queryset=Group.objects.all(), required=False)`).

- **Validación (en serializer):**
  - `validate_password(value)` sobre `password` (método `validate_password` del serializer que invoca el
    validador de Django; traduce errores a `serializers.ValidationError`). Rechaza contraseñas débiles
    con `400`.
  - `username` y `email` únicos (lo aporta el modelo `User`/`UniqueValidator`; el `email` puede no ser
    único por defecto — si se desea unicidad, añadir `UniqueValidator(queryset=User.objects.all())` y
    documentarlo). **Decisión:** exigir `email` único vía `UniqueValidator`, mensaje en español.
- **`create(self, validated_data)`:**
  1. Extraer `groups` y `password` de `validated_data`.
  2. Crear el usuario y asignar la contraseña con `user.set_password(password)` (NUNCA guardar la
     contraseña en claro ni pasarla al constructor del modelo).
  3. `user.save()`.
  4. Asignar la M2M: `user.groups.set(groups)` (tras crear, porque M2M requiere PK).
  5. Devolver el usuario.

### T3.3 — `UserUpdateSerializer` (escritura — edición)

`ModelSerializer` sobre `User`. Igual que create **pero sin `password`** (la contraseña se cambia solo
por la acción dedicada T5.3). Permite editar `username`, `email`, `first_name`, `last_name`,
`is_active`, `is_staff`, `is_superuser`, `groups`.

- **Validación:** `username` y `email` únicos **excluyendo la instancia actual** (los `UniqueValidator`
  de DRF lo manejan al pasar `instance`).
- **`update(self, instance, validated_data)`:** actualizar campos escalares y, si viene `groups`,
  `instance.groups.set(groups)`. No tocar `password`.

### T3.4 — `SetPasswordSerializer` (cambio de contraseña)

`serializers.Serializer` con un único campo `password` (`write_only=True`, `required=True`) validado con
`validate_password` (igual que T3.2). No referencia al modelo; lo consume la acción `set-password`.

**Reglas — qué es validación de serializer vs. service:**
- **Serializer:** fortaleza de contraseña (`validate_password`), unicidad de `username`/`email`,
  obligatoriedad de campos, asignación de M2M `groups`, uso de `set_password`.
- No hay reglas de negocio de dominio que requieran un service dedicado; la auditoría se registra desde
  el ViewSet (T5) reutilizando `registrar_auditoria`.

**Criterio de aceptación:** `UserReadSerializer` nunca expone `password`/hash; `UserCreateSerializer`
crea usuarios con contraseña hasheada (`set_password`) y rechaza contraseñas débiles con `400`;
`UserUpdateSerializer` no permite cambiar la contraseña; `groups` se asignan por PK.

---

## T4 — Serializers de grupos y permisos (`apps/common/serializers.py` — EDITAR)

### T4.1 — `GroupSerializer` (CRUD de roles)

`ModelSerializer` sobre `Group`. Campos: `id`, `name`, `permissions`
(`PrimaryKeyRelatedField(many=True, queryset=Permission.objects.all(), required=False)`), y un campo
auxiliar read-only `permissions_detalle` (`SerializerMethodField` o `PermissionSerializer(many=True,
read_only=True)`) que liste `{id, name, codename, app_label}` para la UI.

- **`create`/`update`:** crear/editar el grupo y asignar la M2M con `instance.permissions.set(...)`
  cuando venga `permissions`. `name` único (validador del modelo `Group`).

### T4.2 — `PermissionSerializer` (solo lectura — catálogo)

`ModelSerializer` sobre `Permission`, **todos los campos read-only**. Expone: `id`, `name`, `codename`,
y `content_type` desglosado de forma legible:
- `content_type` → id, más campos auxiliares `app_label` (`source="content_type.app_label"`) y `model`
  (`source="content_type.model"`).

**Criterio de aceptación:** `GroupSerializer` permite crear/editar un rol y asignarle permisos por PK,
y muestra `permissions_detalle` legible; `PermissionSerializer` es de solo lectura y expone
`app_label`/`model` del `content_type`.

---

## T5 — `UserViewSet` (`apps/common/views.py` — EDITAR)

> **Importación del patrón de auditoría:** `AuditedModelViewSet` vive en `apps/convenios/views.py`. Para
> evitar dependencia cruzada innecesaria y mantener `common` como librería base, **definir aquí** una
> mezcla local equivalente o sobrescribir `perform_create`/`perform_update`/`perform_destroy`
> directamente en el ViewSet usando `registrar_auditoria` (mismo comportamiento que
> `AuditedModelViewSet`). **Decisión:** sobrescribir los métodos directamente en cada ViewSet de esta
> feature (sin importar de `convenios`), para no invertir la dirección de dependencias.

- **T5.1** `UserViewSet(viewsets.ModelViewSet)`:
  - `queryset = User.objects.prefetch_related("groups").all()`.
  - `permission_classes = [IsSuperUser]` (este permiso ya exige autenticación).
  - `get_serializer_class`: `UserReadSerializer` en `list`/`retrieve`; `UserCreateSerializer` en
    `create`; `UserUpdateSerializer` en `update`/`partial_update`; `SetPasswordSerializer` en la acción
    `set_password`.
  - `filterset_fields = ["is_active", "is_superuser", "is_staff", "groups"]`.
  - `search_fields = ["username", "email", "first_name", "last_name"]`.
  - `ordering_fields = ["id", "username", "date_joined", "last_login"]`; `ordering = ["id"]`.
- **T5.2** Auditoría en escrituras:
  - `perform_create`: `objeto = serializer.save()` → `registrar_auditoria(self.request.user, "CREAR",
    objeto)`.
  - `perform_update`: `objeto = serializer.save()` → `registrar_auditoria(self.request.user,
    "ACTUALIZAR", objeto)`. (Incluye cambios de `groups` y flags.)
- **T5.3** `destroy` = **desactivación**, NO borrado físico. Sobrescribir:
  ```python
  def destroy(self, request, *args, **kwargs):
      usuario = self.get_object()
      usuario.is_active = False
      usuario.save(update_fields=["is_active"])
      registrar_auditoria(request.user, "DESACTIVAR", usuario,
                          nombre_campo="is_active", valor_anterior=True, valor_nuevo=False)
      return Response(status=204)
  ```
  No invocar `instance.delete()`. (Conserva trazabilidad y FKs `PROTECT`.)
- **T5.4** Acción dedicada de contraseña:
  ```python
  @action(detail=True, methods=["post"], url_path="set-password")
  def set_password(self, request, pk=None):
      usuario = self.get_object()
      ser = SetPasswordSerializer(data=request.data)
      ser.is_valid(raise_exception=True)
      usuario.set_password(ser.validated_data["password"])
      usuario.save(update_fields=["password"])
      registrar_auditoria(request.user, "ACTUALIZAR", usuario, nombre_campo="password")
      return Response({"detalle": "Contraseña actualizada."})
  ```
  No registrar el valor de la contraseña en la auditoría (solo `nombre_campo="password"`).
- **T5.5** Imports: `IsSuperUser` (T2), `registrar_auditoria` (services), los serializers de T3,
  `action`, `Response`, `viewsets`, `User`.

**Reglas — RN/seguridad:** todo restringido a `IsSuperUser` (RNF-SEG-01/02/03). Solo un superadmin puede
crear usuarios o conceder `is_superuser`/`groups` (evita escalación de privilegios). Contraseñas nunca
expuestas; `set_password` siempre. `destroy` no borra.

**Criterio de aceptación:** CRUD operativo solo para superusuario; alta con contraseña válida (`201`) y
rechazo de contraseña débil (`400`); asignación de `groups`; `set-password` cambia la contraseña;
`DELETE` deja `is_active=False` (no borra) y registra `DESACTIVAR`; todas las escrituras quedan en
`bitacora_auditoria`.

---

## T6 — `GroupViewSet` (`apps/common/views.py` — EDITAR)

- **T6.1** `GroupViewSet(viewsets.ModelViewSet)`:
  - `queryset = Group.objects.prefetch_related("permissions").all()`.
  - `serializer_class = GroupSerializer`.
  - `permission_classes = [IsSuperUser]`.
  - `search_fields = ["name"]`; `ordering_fields = ["id", "name"]`; `ordering = ["name"]`.
- **T6.2** Auditoría en escrituras (mismo patrón que T5.2): `perform_create` → `CREAR`;
  `perform_update` → `ACTUALIZAR` (incluye cambios de `permissions`); `perform_destroy` → registrar
  `ELIMINAR` y luego `instance.delete()` (los grupos sí pueden borrarse; no tienen restricción de
  desactivación como los usuarios).

**Reglas:** la asignación de permisos al grupo es validación/operación de serializer (T4.1); la
auditoría se registra desde el ViewSet.

**Criterio de aceptación:** CRUD de roles solo para superusuario; se pueden asignar permisos a un grupo;
cada operación queda auditada.

---

## T7 — `PermissionViewSet` (`apps/common/views.py` — EDITAR)

- **T7.1** `PermissionViewSet(viewsets.ReadOnlyModelViewSet)` (solo `list`/`retrieve`):
  - `queryset = Permission.objects.select_related("content_type").all()`.
  - `serializer_class = PermissionSerializer`.
  - `permission_classes = [IsSuperUser]`.
  - `filterset_fields = ["content_type", "content_type__app_label"]` (filtra por entidad/app).
  - `search_fields = ["name", "codename"]`.
  - `ordering_fields = ["id", "codename"]`; `ordering = ["content_type", "codename"]`.

**Criterio de aceptación:** lista de permisos solo lectura para superusuario; filtrable por
`content_type`/`app_label` y buscable por `name`/`codename`; no permite escritura (`POST/PUT/DELETE` →
`405`).

---

## T8 — Router del módulo (`apps/common/urls.py` — CREAR)

- **T8.1** Crear `apps/common/urls.py` con un `DefaultRouter` que registre:
  - `router.register("users", UserViewSet, basename="user")`
  - `router.register("groups", GroupViewSet, basename="group")`
  - `router.register("permissions", PermissionViewSet, basename="permission")`
- **T8.2** Exponer `urlpatterns = router.urls`. Importar los ViewSets desde `apps.common.views`.
  (T11.4 reestructura este `urlpatterns` para anteponer la ruta standalone del lookup.)

**Criterio de aceptación:** el módulo expone los tres routers; `basename` claros (`user`/`group`/
`permission`).

---

## T9 — Montaje en el API v1 (`config/api_urls.py` — EDITAR)

- **T9.1** Añadir, junto a los `include` de los demás módulos, **sin prefijo extra** (recomendado por
  basenames ya claros):
  ```python
  path("", include("apps.common.urls")),
  ```
- **T9.2** Verificar que no haya colisión de basenames con los routers de `convenios`/`internados`/
  `actividades` (`users`/`groups`/`permissions` no se usan en ellos).

**Decisión documentada:** se monta **sin** prefijo `admin/`; los endpoints quedan en
`/api/v1/users/`, `/api/v1/groups/`, `/api/v1/permissions/`. La restricción de acceso la garantiza
`IsSuperUser`, no la ruta.

**Criterio de aceptación:** los tres endpoints aparecen bajo `/api/v1/` y en el esquema OpenAPI.

---

## T10 — Escritura de perfiles institucionales / scope por objeto (`UserEntityProfile`)

> **Feature aditiva sobre módulo cerrado.** Añade la **escritura del alcance por objeto** (row-level):
> otorgar a un usuario acceso a una o varias **entidades institucionales** (universidades, IPRESS,
> GERESA, etc.) bajo un **rol** (`Group`). Complementa el sistema de permisos por app/modelo (Django
> Groups → Permissions, ya cubierto en T3–T7) con el **ámbito por entidad** que consumen
> `HasEntityScope`/`exigir_ambito` (`apps/common/permissions.py`). **No** crea modelos ni migraciones: el
> modelo `UserEntityProfile` ya existe (`apps/convenios/models.py:490`, tabla `perfil_usuario_entidad`;
> schema en `docs/db_schema_modulo_01_convenios.md` §7 — **no** duplicar aquí su definición).

### Diseño y decisiones (leer antes de implementar)

- **Patrón: sub-recurso dedicado de usuarios (Opción A).** `GET/POST/DELETE
  /api/v1/users/{id}/profiles/`. **No** anidar la escritura de perfiles en `UserCreateSerializer`/
  `UserUpdateSerializer` (T3): mantiene esos serializers ya validados sin reabrir, permite **auditoría
  granular** por alta/baja, concentra el control **anti-escalación** en un único punto y es coherente
  con el patrón `@action` de `UserViewSet` (T5). Se implementa como `@action(detail=True,
  methods=["get", "post", "delete"], url_path="profiles")` sobre `UserViewSet`.

- **Payload: genérico** `{ "rol": <group_id>, "tipo_entidad": "university", "ids": [3, 7] }`.
  - El FK del modelo es **polimórfico** (`tipo_contenido` → `ContentType`), por lo que sirve para
    `university`, `ipress`, `student`, `geresa`, etc. Un payload específico `{universidades:[...]}`
    cerraría la puerta a los demás tipos y obligaría a un endpoint por entidad. Se elige el **genérico**.
  - **Vocabulario consistente con la lectura ya publicada** (`docs/api_accesos_frontend.md` §1;
    `UserEntityProfileSerializer`, `apps/common/serializers.py:41`): se usa `tipo_entidad` (nombre de
    modelo en minúscula, `source` = `tipo_contenido.model`), `id_objeto` (en la respuesta) y `rol`
    (nombre del `Group` en la salida; su id en la entrada).
    - **Entrada:** `rol` acepta el **id** del `Group` (`PrimaryKeyRelatedField`); `tipo_entidad` es el
      `model` en minúscula del `ContentType` (string, p. ej. `"university"`); `ids` es la lista de PKs de
      las entidades. Se resuelve el `ContentType` por `model` acotado a las apps del proyecto
      (`convenios`, `internados`, `actividades`) para evitar ambigüedad de nombres de modelo.
    - **Salida:** cada perfil se serializa con la **misma forma que la lectura** — `{ tipo_entidad,
      id_objeto, entidad, rol }` (reutilizar la forma de `UserEntityProfileSerializer`), añadiendo `id`
      (PK del perfil) y `activo` para permitir la baja/re-alta.

- **Semántica de escritura:**
  - **POST materializa N filas en una operación** (una por cada id de `ids`) para el `(usuario, rol,
    tipo_entidad)` dado, dentro de una única `transaction.atomic()`.
  - **Idempotente respecto de `unique_together` `(usuario, tipo_contenido, id_objeto, grupo)`:** para
    cada `(usuario, tipo_contenido, id_objeto, grupo)` se hace `update_or_create` con `activo=True`. Si
    el perfil ya existía **activo**, no se duplica ni se audita (no hay cambio); si existía **inactivo**,
    se **reactiva** (`activo=False→True`) y se audita como `ACTIVAR`; si no existía, se **crea** y se
    audita como `CREAR`. Reenviar el mismo POST no produce cambios ni auditoría redundante.
  - **DELETE = baja lógica (`activo=False`), no borrado físico.** Justificación: el modelo tiene el
    campo `activo` (default `True`) y todos los selectores de lectura filtran `activo=True`
    (`perfiles_del_usuario`, `apps/common/selectors.py:14`); la baja lógica **preserva trazabilidad**
    (RNF-AUD) y respeta el `unique_together` (un mismo vínculo puede reactivarse luego sin recrear PK ni
    chocar con la restricción de unicidad). Se audita como `DESACTIVAR`. El DELETE opera sobre un
    **perfil concreto**: `DELETE /api/v1/users/{id}/profiles/?profile_id=<pk>` (o `{ "profile_id": <pk>
    }` en el body). Si el perfil ya estaba inactivo, respuesta idempotente `204` sin nueva auditoría.
  - **GET** lista los perfiles del usuario objetivo. Por defecto solo los **activos**; admite
    `?incluir_inactivos=true` para ver también los dados de baja (auditoría / UI de re-alta).

- **Validaciones (marca de capa):**
  - **Serializer (`400`):** el `rol` (`group_id`) debe existir → `PrimaryKeyRelatedField(queryset=
    Group.objects.all())`; `ids` no vacío y de enteros; `tipo_entidad` debe corresponder a un
    `ContentType` **existente y admitido** (a partir de T11, la allowlist `ASSIGNABLE_PROFILE_MODELS`) —
    si no, `ValidationError` en español. **Existencia de cada id para el `tipo_contenido` dado:** el
    serializer verifica que cada PK de `ids` exista en el modelo resuelto por el `ContentType`
    (`content_type.model_class().objects.filter(pk__in=ids)`); los ids que no existan se rechazan con
    `400` listándolos.
  - **Coherencia con RN-20 (1..N):** el modelo admite de **1 a N** entidades por usuario/rol; el
    endpoint no impone tope superior (RN-20 habla de 1..N universidades). Se exige **al menos un id**
    (`ids` no vacío) por operación.
  - **No es lógica de dominio con service dedicado:** la materialización idempotente y la auditoría
    viven en la **acción del ViewSet** (mismo criterio que T5/T6, que auditan desde el ViewSet). El
    serializer solo valida forma y existencia. No se crea un service en `apps/common/services.py` para
    esto.

- **Ubicación cross-app (resolución explícita del conflicto de dependencias):** el modelo
  `UserEntityProfile` vive en `apps/convenios`, pero **`apps/common` ya importa desde
  `apps.convenios.models` en producción** (`apps/common/selectors.py:6` importa `UserEntityProfile`;
  `apps/common/services.py:6` importa `AuditLog`/`Document`). Por tanto la nota original del spec
  —"mantener `common` sin importar desde `convenios`"— **no reflejaba el código real** y aplica solo al
  patrón de **ViewSets de auditoría** (no importar `AuditedModelViewSet` desde `convenios.views`), no a
  los **modelos**. **Decisión:** el ViewSet (acción `profiles`) y los serializers de esta feature viven
  en `apps/common` (`views.py`/`serializers.py`), importan `UserEntityProfile` **puntualmente** desde
  `apps.convenios.models` (mismo patrón ya usado por el selector) y reutilizan la auditoría local
  (`registrar_auditoria`, sin importar de `convenios.views`). La resolución de `ContentType`/entidades se
  hace vía `django.contrib.contenttypes.models.ContentType`, sin acoplarse a serializers de `convenios`.

- **Permisos:** `permission_classes = [IsSuperUser]` (T2), heredado del `UserViewSet`. **Solo el
  superadministrador** otorga o revoca scope por objeto. Anti-escalación: quien concede alcance no debe
  poder auto-elevarse; es coherente con que solo el superadmin asigna `groups`/`is_superuser` en T5
  (RNF-SEG-01/02/03). El rol `Administrador RENADS` queda **fuera** de la escritura de scope en este
  spec para no abrir un vector de auto-elevación; si en el futuro se requiere, se decide en un spec
  posterior.

- **Auditoría (RNF-AUD-01/02):** cada fila materializada/reactivada/dada de baja se audita **por
  separado** con `registrar_auditoria(self.request.user, <accion>, perfil)` sobre la instancia
  `UserEntityProfile`, dentro de la misma transacción:
  - alta nueva → `CREAR`;
  - reactivación de un perfil inactivo → `ACTIVAR` (`nombre_campo="activo"`, `valor_anterior=False`,
    `valor_nuevo=True`);
  - baja lógica → `DESACTIVAR` (`nombre_campo="activo"`, `valor_anterior=True`, `valor_nuevo=False`).

### Tareas

- **T10.1 — `UserEntityProfileWriteSerializer` (entrada) (`apps/common/serializers.py` — EDITAR)**
  `serializers.Serializer` con:
  - `rol` = `PrimaryKeyRelatedField(queryset=Group.objects.all(), required=True)` (mensaje de error en
    español si no existe).
  - `tipo_entidad` = `CharField(required=True)` — `model` en minúscula del `ContentType`.
  - `ids` = `ListField(child=IntegerField(), allow_empty=False, required=True)`.
  - `validate_tipo_entidad`: resuelve el `ContentType` por `model`. **A partir de T11.5** valida contra
    la allowlist `ASSIGNABLE_PROFILE_MODELS` (fuente única compartida con el lookup); si el `model` no
    pertenece a la allowlist → `ValidationError` («El tipo de entidad indicado no es válido o no es
    asignable a un perfil.»). Deja disponible el `ContentType` resuelto para el `validate`.
  - `validate`: con el `ContentType` resuelto, comprueba que cada PK de `ids` exista en su modelo
    (`content_type.model_class().objects.filter(pk__in=ids)`); si faltan, `ValidationError` en español
    listando los ids inexistentes. Deja disponibles en `validated_data` el `ContentType` (`tipo_contenido`),
    el `Group` (`rol`) y los `ids` validados.
  - Docstrings/help_text/mensajes en español; nombres de clase en inglés. Los nombres de campo del
    payload (`rol`, `tipo_entidad`, `ids`) se mantienen para consistencia con la lectura publicada.

- **T10.2 — `UserEntityProfileWriteReadSerializer` (salida) (`apps/common/serializers.py` — EDITAR)**
  Serializer de salida que **extiende la forma de `UserEntityProfileSerializer`** (los 4 campos ya
  publicados: `tipo_entidad`, `id_objeto`, `entidad`, `rol`) añadiendo `id` (PK del perfil) y `activo`
  para la gestión de bajas/re-altas. Puede ser una subclase de `UserEntityProfileSerializer` o un
  serializer nuevo con los mismos `source`. **No modificar** `MeSerializer` ni el
  `UserEntityProfileSerializer` original (esos siguen sirviendo `/auth/me/` con exactamente 4 campos).

- **T10.3 — Acción `profiles` en `UserViewSet` (`apps/common/views.py` — EDITAR)**
  Añadir `@action(detail=True, methods=["get", "post", "delete"], url_path="profiles")`:
  - Importar `UserEntityProfile` puntualmente: `from apps.convenios.models import UserEntityProfile`
    (mismo patrón que el selector). Importar `ContentType` si hace falta y los serializers de T10.
  - **GET:** `perfiles = UserEntityProfile.objects.filter(usuario=usuario).select_related(
    "tipo_contenido", "grupo")`; por defecto `.filter(activo=True)`, salvo `?incluir_inactivos=true`.
    Devolver `UserEntityProfileWriteReadSerializer(perfiles, many=True).data` (`200`).
  - **POST:** validar con `UserEntityProfileWriteSerializer`; dentro de `transaction.atomic()`, por cada
    id hacer `update_or_create(usuario=usuario, tipo_contenido=<ct>, id_objeto=id, grupo=<group>,
    defaults={"activo": True})`; auditar `CREAR`/`ACTIVAR` según haya sido creado o reactivado (comparar
    el flag `created` y el estado previo de `activo`). Responder `201` con la lista resultante serializada
    (`UserEntityProfileWriteReadSerializer`).
  - **DELETE:** requiere `profile_id` (query param o body); localizar el `UserEntityProfile` del
    `usuario`; si está activo, `activo=False` + `save(update_fields=["activo"])` + auditar `DESACTIVAR`;
    responder `204` (idempotente si ya estaba inactivo). Si el `profile_id` no pertenece al usuario →
    `404`; si falta `profile_id` → `400`.
  - En `get_serializer_class` de `UserViewSet` (T5), devolver `UserEntityProfileWriteSerializer` cuando
    `self.action == "profiles"` (para el esquema OpenAPI), o documentar el body con `@extend_schema`.

- **T10.4 — Documentación OpenAPI y contrato**
  Decorar la acción con `@extend_schema` (request=`UserEntityProfileWriteSerializer`,
  responses=`UserEntityProfileWriteReadSerializer(many=True)`) para que el sub-recurso aparezca en el
  esquema. Mantener la salida alineada con `docs/api_accesos_frontend.md` (`tipo_entidad`/`id_objeto`/
  `entidad`/`rol`, más `id`/`activo` propios de la gestión). No es necesario reescribir
  `docs/api_accesos_frontend.md`, pero el validator debe confirmar la consistencia del vocabulario.

### Criterios de aceptación (T10)

1. `POST /api/v1/users/{id}/profiles/` con `{ "rol": <group_id>, "tipo_entidad": "university", "ids":
   [3, 7] }` (superadmin) → `201`; se materializan/reactivan las filas en `perfil_usuario_entidad` y
   aparecen en `GET /api/v1/auth/me/` del usuario objetivo con la forma `{tipo_entidad, id_objeto,
   entidad, rol}`.
2. **Idempotencia:** reenviar el mismo POST no crea duplicados (respeta `unique_together`) ni genera
   auditoría redundante; el conteo de filas activas no cambia.
3. **Reactivación:** un `id` que apunta a un perfil previamente dado de baja lo reactiva (`activo`
   `False→True`) y registra `ACTIVAR`.
4. **DELETE** `?profile_id=<pk>` → `204`; el perfil queda `activo=False` (no borrado), desaparece de
   `/auth/me/` y de `GET .../profiles/` por defecto, pero aparece con `?incluir_inactivos=true`; registra
   `DESACTIVAR`. Idempotente si ya estaba inactivo.
5. **Validaciones `400`:** `rol` inexistente; `tipo_entidad` no admitida/desconocida; `ids` vacío; algún
   id inexistente para el `tipo_entidad` dado — todos con mensaje en español. `profile_id` ausente en
   DELETE → `400`; `profile_id` ajeno al usuario → `404`.
6. **Permisos:** usuario **no** superadmin (o anónimo) → `403` en GET/POST/DELETE de `.../profiles/`.
7. **Auditoría:** cada alta/reactivación/baja deja su registro (`CREAR`/`ACTIVAR`/`DESACTIVAR`) en
   `bitacora_auditoria` con `usuario`, `tipo_contenido` = `UserEntityProfile`, `id_objeto` = PK del
   perfil.
8. **Sin migraciones:** `python manage.py makemigrations` sigue saliendo vacío (no se tocan modelos).
9. **Genericidad:** el mismo endpoint funciona con `tipo_entidad: "ipress"` (u otra entidad admitida) sin
   cambios de código.

---

## T11 — Lookup de tipos de entidad asignables (destrabar el alta de perfiles)

> **Feature aditiva que complementa a T10** (ya implementada y validada). T10 expone la escritura del
> scope por objeto (`GET/POST/DELETE /api/v1/users/{id}/profiles/`) y recibe `tipo_entidad` como el
> **nombre de modelo en minúscula** (p. ej. `"university"`). Sin embargo, el frontend no tiene de dónde
> obtener la **lista de tipos de entidad válidos** ni sus **etiquetas legibles**, por lo que la pantalla
> `/usuarios/perfiles` mantiene el alta deshabilitada (`disableCreate:true`). **T11 crea ese lookup** —
> un endpoint de solo lectura que alimenta el selector «Tipo de entidad» del alta de perfiles — y
> **endurece la validación de T10** para que ambos compartan una **única allowlist** de modelos
> asignables. **No** crea modelos ni migraciones; **no** crea tests (regla MVP).

### Problema que resuelve

- El write de T10 espera `tipo_entidad` = `model` en minúscula, pero el cliente no dispone del catálogo
  de tipos elegibles ni de nombres legibles en español.
- La validación actual de T10 (`UserEntityProfileWriteSerializer.validate_tipo_entidad`,
  `apps/common/serializers.py:309`) admite **cualquier** modelo de las apps `convenios`/`internados`/
  `actividades` (constante `APPS_ENTIDADES_ADMITIDAS`, `apps/common/serializers.py:277`). Eso permite
  asignar perfiles sobre modelos **no institucionales** (p. ej. `document`, `auditlog`, `campoclinico`,
  `historialestadoconvenio`), lo cual no tiene sentido de negocio y ensucia el scope por objeto.

### Precedente a imitar (mismo patrón, ya en el repo)

`SolicitanteContentTypeView` (`apps/convenios/views.py:569`) + `SolicitanteContentTypeSerializer`
(`apps/convenios/serializers.py:74`) + ruta `path("solicitante-content-types/", ...)`
(`apps/convenios/urls.py:27`, fuera del router). Reproducir la misma estructura (allowlist de modelos +
`APIView` con `get()` que resuelve `ContentType.objects.get_for_models(*MODELS)` + serializer de salida +
ruta standalone), adaptada a la administración de perfiles.

### Diseño y decisiones (leer antes de implementar)

- **D1 — Allowlist `ASSIGNABLE_PROFILE_MODELS` (fuente única compartida).** Constante — una tupla de
  clases de modelo — que define **exactamente** las entidades institucionales sobre las que tiene sentido
  otorgar alcance a un usuario. Es la **misma** constante que consumen el lookup (T11) **y** la
  validación del write de T10 (subtarea T11.5): así el catálogo que ofrece el lookup y el conjunto que
  acepta el POST de perfiles **no pueden divergir**. Vive en `apps/common/serializers.py` (junto a
  `UserEntityProfileWriteSerializer`, que ya importa modelos de `convenios`), y el ViewSet/lookup la
  importa desde allí para no duplicarla.

  **Conjunto exacto (incluidos) y justificación por RN:**

  | Modelo | App | `tipo_entidad` (`model`) | `label` (`verbose_name`) | Motivo de inclusión |
  |--------|-----|--------------------------|--------------------------|---------------------|
  | `University` | `convenios` | `university` | «universidad» | RN-20: el rol `Universidad` registra internos; su alcance es 1..N universidades (`perfil_usuario_entidad`). Núcleo del scope. |
  | `Ipress` | `convenios` | `ipress` | «IPRESS» | Sedes docentes autorizadas por CONAPRES; los actores de sede tienen alcance por IPRESS. |
  | `RegionalGovernment` | `convenios` | `regionalgovernment` | «gobierno regional» | GORE que administra órganos regionales; alcance de usuarios GORE. |
  | `RegionalOrgan` | `convenios` | `regionalorgan` | «órgano regional» | GERESA/DIRESA/DIRIS: asignan campos clínicos por universidad/carrera; alcance institucional propio. |
  | `ExecutingUnit` | `convenios` | `executingunit` | «unidad ejecutora» | Unidad ejecutora que administra IPRESS; nivel intermedio del ámbito sanitario. |
  | `Conapres` | `convenios` | `conapres` | «CONAPRES» | Autoriza/registra sedes docentes y campos clínicos; alcance de usuarios CONAPRES. |
  | `MinsaOrgan` | `convenios` | `minsaorgan` | «órgano del MINSA» | DIGEP/OGAJ/SG/VICEPAS: órganos MINSA con usuarios de alcance institucional. |
  | `Student` | `internados` | `student` | «estudiante» | **RN-22 (onboarding del interno):** al registrar el internado se crea un `User` con `perfil_usuario_entidad` **sobre su `Student`** (grupo `Interno`), con acceso de solo lectura a sus datos y adjunto de sus DJ. El scope del rol `Interno` es por `Student`. |

  Los `label` provienen de `Model._meta.verbose_name` verificado en los modelos
  (`apps/convenios/models.py`: universidad/IPRESS/gobierno regional/órgano regional/unidad ejecutora/
  CONAPRES/órgano del MINSA; `apps/internados/models.py:151`: estudiante).

  **Excluidos explícitamente (y por qué):** cualquier otro modelo de `convenios`/`internados`/
  `actividades` que **no** sea una entidad institucional sujeta a alcance — p. ej. `Document`,
  `AuditLog`, `UserEntityProfile`, `Convention`, `ClinicalField`, `Representative`,
  `UniversityAuthority`, `Faculty`, `Career`, catálogos y tablas de historial. No son entidades sobre las
  que se conceda un rol con ámbito; incluirlas abriría scopes sin sentido de negocio y contradiría
  RN-20/RN-22. **Nota:** los modelos de la app `actividades` **no** entran en la allowlist en este spec
  (no hay rol cuyo alcance sea una actividad); si en el futuro se requiere, se decide en spec posterior.

- **D2 — Contrato de salida.** Cada item expone:
  - `tipo_entidad` — el **`model` en minúscula** (`ContentType.model`), **exactamente el mismo string**
    que consume el write de T10 (p. ej. `"university"`, `"student"`). Este es el campo que el frontend
    reenvía en el POST de perfiles. Vocabulario alineado con `docs/api_accesos_frontend.md` §1 y con
    `UserEntityProfileSerializer` (`apps/common/serializers.py:45`, `source="tipo_contenido.model"`).
  - `label` — **etiqueta legible en español**, derivada de `Model._meta.verbose_name`
    (p. ej. «universidad», «IPRESS», «órgano regional», «estudiante»). Para presentación en el selector;
    aplicar capitalización en el frontend si se desea.
  - `app_label` — app de Django del modelo (p. ej. `convenios`, `internados`). Para consistencia con el
    precedente y para desambiguar en la UI.
  - `id` — **se incluye** el `ContentType.id`, por **consistencia con el precedente**
    (`SolicitanteContentTypeSerializer` lo expone). **Decisión documentada:** T10 **no** lo necesita
    (su write resuelve el `ContentType` a partir del string `tipo_entidad`, no del id); se expone solo por
    paridad con el precedente y como dato informativo. El frontend debe usar `tipo_entidad` (string), no
    `id`, para el POST de perfiles.

  **Orden:** salida ordenada de forma **estable por `label`** (alfabético en español), para que el
  selector del frontend salga ordenado sin trabajo adicional. (El precedente ordena por `id`; aquí se
  prefiere `label` por ergonomía de UI — decisión documentada.)

- **D3 — Ruta, view y serializer (ubicación).**
  - **Ubicación: `apps/common`**, junto al `UserViewSet`/T10. Respeta la dirección de dependencias: la
    allowlist y la validación viven en `apps/common/serializers.py`, que **ya importa** modelos de
    `convenios` (patrón existente, ver T10 y `apps/common/selectors.py:6`). No se invierte ninguna
    dependencia nueva.
  - **View:** `AssignableEntityTypeView(APIView)` en `apps/common/views.py`.
  - **Serializer de salida:** `AssignableEntityTypeSerializer` en `apps/common/serializers.py`.
  - **Ruta:** standalone (fuera del router), montada en `apps/common/urls.py` (T8) como
    `path("profile-entity-types/", AssignableEntityTypeView.as_view(), name="profile-entity-types")`.
    **Nombre de ruta elegido: `profile-entity-types`** (evita `content-types` a secas — que sería
    ambiguo — y deja claro que son los tipos de entidad elegibles para **perfiles** de usuario). Queda
    expuesto como `GET /api/v1/profile-entity-types/`.

- **D4 — Permisos.** `permission_classes = [IsSuperUser]` (T2). **Decisión y justificación:** el lookup
  solo alimenta el selector de la **administración de perfiles**, que es un flujo exclusivo del
  superadministrador (coherente con T5/T10, todos `IsSuperUser`). Aunque el precedente
  (`SolicitanteContentTypeView`) usa `IsAuthenticated`, aquí se elige **`IsSuperUser`** para **no filtrar
  el catálogo de administración a roles sin acceso** a esa pantalla (RNF-SEG-01/02/03, principio de menor
  exposición). Un no-superadmin recibe `403`.

- **D5 — Endurecimiento de la validación de T10 (fuente única).**
  `UserEntityProfileWriteSerializer.validate_tipo_entidad` (`apps/common/serializers.py:309`) deja de
  validar contra `APPS_ENTIDADES_ADMITIDAS` (cualquier modelo de las tres apps) y pasa a validar contra
  la **misma allowlist** `ASSIGNABLE_PROFILE_MODELS`. Así, lookup (T11) y validación de escritura (T10)
  **comparten una única fuente de verdad**: solo los tipos que devuelve el lookup son aceptados por el
  POST de perfiles. Un `tipo_entidad` fuera de la allowlist (p. ej. `"document"`) → `400` con mensaje en
  español. La constante `APPS_ENTIDADES_ADMITIDAS` puede conservarse solo si algún otro punto la usa; de
  lo contrario, retirarla para no dejar código muerto (documentar la decisión del implementador).

### Tareas

- **T11.1 — Allowlist `ASSIGNABLE_PROFILE_MODELS` (`apps/common/serializers.py` — EDITAR).**
  Definir la tupla de clases de modelo del cuadro de D1, importando `University`, `Ipress`,
  `RegionalGovernment`, `RegionalOrgan`, `ExecutingUnit`, `Conapres`, `MinsaOrgan` de
  `apps.convenios.models` y `Student` de `apps.internados.models`. Comentario en español que la marque
  como **fuente única** compartida por el lookup (T11) y la validación del write (T10). Colocarla cerca de
  `UserEntityProfileWriteSerializer` para que ambos la referencien sin importaciones circulares.

- **T11.2 — `AssignableEntityTypeSerializer` (salida) (`apps/common/serializers.py` — EDITAR).**
  `serializers.Serializer` (mismo estilo que `SolicitanteContentTypeSerializer`) con:
  - `id = IntegerField(help_text="ID del ContentType (informativo; el write usa tipo_entidad)")`,
  - `tipo_entidad = CharField(help_text="Nombre de modelo en minúscula; valor que espera el POST de perfiles (p. ej. university, student)")`,
  - `label = CharField(help_text="Etiqueta legible en español (verbose_name del modelo)")`,
  - `app_label = CharField(help_text="App de Django (p. ej. convenios, internados)")`.
  Docstring en español. Nombre de clase en inglés.

- **T11.3 — `AssignableEntityTypeView(APIView)` (`apps/common/views.py` — EDITAR).**
  - `permission_classes = [IsSuperUser]` (importar `IsSuperUser` de T2).
  - `get(self, request)`: resolver `cts = ContentType.objects.get_for_models(*ASSIGNABLE_PROFILE_MODELS)`
    (importar `ContentType` y la allowlist de `apps.common.serializers`). Para cada `(modelo, ct)` en
    `cts.items()`, construir `{ "id": ct.id, "tipo_entidad": ct.model, "label":
    modelo._meta.verbose_name, "app_label": ct.app_label }`. Ordenar por `label` (estable). Devolver
    `AssignableEntityTypeSerializer(data, many=True).data` (`200`).
  - Decorar con `@extend_schema(responses=AssignableEntityTypeSerializer(many=True), summary="Tipos de
    entidad asignables a perfiles", description=..., tags=["common"])` en español, análogo al precedente.

- **T11.4 — Ruta standalone (`apps/common/urls.py` — EDITAR).**
  Reestructurar `urlpatterns` de T8 para anteponer la ruta standalone al `*router.urls` (mismo patrón que
  `apps/convenios/urls.py:26`):
  ```python
  urlpatterns = [
      path("profile-entity-types/", AssignableEntityTypeView.as_view(), name="profile-entity-types"),
      *router.urls,
  ]
  ```
  Importar `path` de `django.urls` y `AssignableEntityTypeView` de `apps.common.views`. Queda montada bajo
  `/api/v1/` por el `include("apps.common.urls")` ya existente (T9); **no** tocar `config/api_urls.py`.

- **T11.5 — Endurecer `validate_tipo_entidad` de T10 (`apps/common/serializers.py` — EDITAR).**
  Modificar `UserEntityProfileWriteSerializer.validate_tipo_entidad` para validar contra
  `ASSIGNABLE_PROFILE_MODELS` en lugar de `APPS_ENTIDADES_ADMITIDAS`. Implementación sugerida: resolver el
  conjunto de `ContentType` admitidos con `ContentType.objects.get_for_models(*ASSIGNABLE_PROFILE_MODELS)`
  y aceptar el `model` (minúscula) solo si coincide con uno de ellos; si no, `ValidationError`
  («El tipo de entidad indicado no es válido o no es asignable a un perfil.»). Conservar el resto del
  flujo de T10 (resolución del `ContentType`, verificación de existencia de `ids` en `validate`) sin
  cambios funcionales. Si `APPS_ENTIDADES_ADMITIDAS` queda sin uso, retirarla (evitar código muerto).

### Criterios de aceptación (T11)

1. `GET /api/v1/profile-entity-types/` (superadmin) → `200` con una lista de items
   `{ id, tipo_entidad, label, app_label }`, uno por cada modelo de `ASSIGNABLE_PROFILE_MODELS`
   (8 entradas: `university`, `ipress`, `regionalgovernment`, `regionalorgan`, `executingunit`,
   `conapres`, `minsaorgan`, `student`). `label` en español (verbose_name); ordenada de forma estable por
   `label`.
2. **Contrato reutilizable por T10:** el `tipo_entidad` de cada item (string en minúscula) es aceptado
   sin cambios por `POST /api/v1/users/{id}/profiles/` como `tipo_entidad` — el front puede tomar el
   valor del lookup y reenviarlo directamente.
3. **Permisos:** un usuario **no** superadmin (o anónimo) recibe `403` en
   `GET /api/v1/profile-entity-types/`.
4. **Validación endurecida (T10):** `POST /api/v1/users/{id}/profiles/` con `tipo_entidad` **fuera** de
   la allowlist (p. ej. `"document"`, `"auditlog"`, `"campoclinico"`) → `400` con mensaje en español; con
   un `tipo_entidad` de la allowlist (p. ej. `"student"`, RN-22) sigue funcionando (`201`). Lookup y
   validación comparten `ASSIGNABLE_PROFILE_MODELS`.
5. **Sin migraciones:** `python manage.py makemigrations` sigue saliendo vacío.
6. **OpenAPI:** el path `profile-entity-types` aparece en el esquema (`spectacular`) con la respuesta
   `AssignableEntityTypeSerializer(many=True)`.
7. **Idioma:** nombres de clase/endpoint/campo en inglés; docstrings/`help_text`/mensajes/`label` en
   español.

---

## Verificación (cierre)

1. `python manage.py check` sin errores (activar antes `.venv\Scripts\Activate.ps1`).
2. `python manage.py makemigrations` **no** debe generar migraciones nuevas (no se crean modelos).
3. `python manage.py spectacular --file schema.yml` (o `/api/schema/`) genera sin error e incluye los
   paths `users`, `groups`, `permissions`, el sub-recurso `users/{id}/profiles/` y el lookup
   `profile-entity-types` (T11).
4. Ejecutar `/code-review` antes de cerrar (sin tests automatizados, regla MVP).
5. **Guía de pruebas manuales** (criterio funcional; registrar en
   `spec/common_usuarios.guia_pruebas.md`):
   - `POST /api/v1/auth/token/` → la respuesta incluye `es_superusuario`, `nombre`, `grupos`; el JWT
     decodificado contiene el claim `es_superusuario`.
   - Como **superadmin**: `POST /api/v1/users/` con contraseña válida → `201`; con contraseña débil →
     `400` con mensaje en español.
   - `PATCH /api/v1/users/{id}/` asignando `groups` → `200`; verificar M2M.
   - `POST /api/v1/users/{id}/set-password/` con contraseña válida → `200`; débil → `400`.
   - `DELETE /api/v1/users/{id}/` → `204`; el usuario queda `is_active=False` (no borrado); registro
     `DESACTIVAR` en `bitacora_auditoria`.
   - CRUD de `groups`: crear rol, asignarle `permissions`, editar y eliminar.
   - `GET /api/v1/permissions/?content_type__app_label=convenios` filtra; búsqueda por `codename`.
   - Como **NO superusuario** (o anónimo): `403` en `users`, `groups`, `permissions` (todos los métodos).
   - **Scope por objeto (T10):** como superadmin, `POST /api/v1/users/{id}/profiles/` con
     `{rol, tipo_entidad:"university", ids:[...]}` → `201`; verificar filas en `perfil_usuario_entidad`
     y en `GET /api/v1/auth/me/` del usuario objetivo. Reenviar el mismo POST → sin duplicados
     (idempotencia). `DELETE .../profiles/?profile_id=<pk>` → `204` y `activo=False` (baja lógica);
     reactivación vía POST del mismo id → `ACTIVAR`. `400` para `rol`/`tipo_entidad`/`ids` inválidos.
     Como NO superadmin → `403`.
   - **Lookup de tipos de entidad asignables (T11):** como **superadmin**,
     `GET /api/v1/profile-entity-types/` → `200` con 8 items `{id, tipo_entidad, label, app_label}`
     (`university`, `ipress`, `regionalgovernment`, `regionalorgan`, `executingunit`, `conapres`,
     `minsaorgan`, `student`), ordenados por `label` en español. Tomar un `tipo_entidad` del lookup
     (p. ej. `"student"`) y usarlo en `POST /api/v1/users/{id}/profiles/` → `201` (contrato reutilizable).
     `POST` de perfiles con `tipo_entidad:"document"` (fuera de la allowlist) → `400` en español
     (validación endurecida, misma fuente `ASSIGNABLE_PROFILE_MODELS`). Como **NO superadmin** o anónimo:
     `GET /api/v1/profile-entity-types/` → `403`.
   - Verificar registros `CREAR`/`ACTUALIZAR`/`DESACTIVAR` de usuarios; `CREAR`/`ACTUALIZAR`/`ELIMINAR`
     de grupos; y `CREAR`/`ACTIVAR`/`DESACTIVAR` de perfiles institucionales en `bitacora_auditoria`.

## Endpoints resultantes

| Método(s) | Endpoint | ViewSet | Permisos |
|-----------|----------|---------|----------|
| POST | `/api/v1/auth/token/` | `CustomTokenObtainPairView` (enriquecido) | público (credenciales) |
| GET / POST | `/api/v1/users/` | `UserViewSet` | `IsSuperUser` |
| GET / PUT / PATCH / DELETE | `/api/v1/users/{id}/` | `UserViewSet` (DELETE = desactivar) | `IsSuperUser` |
| POST | `/api/v1/users/{id}/set-password/` | `UserViewSet` (action) | `IsSuperUser` |
| GET / POST / DELETE | `/api/v1/users/{id}/profiles/` | `UserViewSet` (action `profiles`, T10) | `IsSuperUser` |
| GET | `/api/v1/profile-entity-types/` | `AssignableEntityTypeView` (lookup, T11) | `IsSuperUser` |
| GET / POST | `/api/v1/groups/` | `GroupViewSet` | `IsSuperUser` |
| GET / PUT / PATCH / DELETE | `/api/v1/groups/{id}/` | `GroupViewSet` | `IsSuperUser` |
| GET | `/api/v1/permissions/` | `PermissionViewSet` | `IsSuperUser` |
| GET | `/api/v1/permissions/{id}/` | `PermissionViewSet` | `IsSuperUser` |

## Referencias

- **Modelos nativos Django:** `django.contrib.auth.models.User` (`auth_user`), `Group` (`auth_group`),
  `Permission` (`auth_permission`), M2M `auth_user_groups` / `auth_group_permissions`. No inventar
  campos: usar los del modelo estándar.
- **Modelo de scope (T10):** `UserEntityProfile` (`apps/convenios/models.py:490`, tabla
  `perfil_usuario_entidad`) — `usuario` + `tipo_contenido` (ContentType) + `id_objeto` + `grupo`
  (`auth.Group`, `PROTECT`) + `activo` (default `True`); `unique_together (usuario, tipo_contenido,
  id_objeto, grupo)`. Schema en `docs/db_schema_modulo_01_convenios.md` §7 y ER en
  `docs/db_schema_er_global.md`.
- **Modelos de entidad institucional (allowlist T11):** `University`, `Ipress`, `RegionalGovernment`,
  `RegionalOrgan`, `ExecutingUnit`, `Conapres`, `MinsaOrgan` (`apps/convenios/models.py`); `Student`
  (`apps/internados/models.py:102`, `verbose_name = "estudiante"`). Schema en
  `docs/db_schema_modulo_01_convenios.md` y `docs/db_schema_modulo_02_internados.md`.
- **Precedente del lookup (T11):** `SolicitanteContentTypeView` (`apps/convenios/views.py:569`),
  `SolicitanteContentTypeSerializer` (`apps/convenios/serializers.py:74`), ruta standalone en
  `apps/convenios/urls.py:27`.
- **Auth existente:** `CustomTokenObtainPairSerializer` y `MeSerializer`
  (`apps/common/serializers.py`); `CustomTokenObtainPairView`/`MeView` (`apps/common/views.py`); rutas
  en `config/api_urls.py`.
- **Lectura de scope ya publicada (contrato a mantener):** `UserEntityProfileSerializer`
  (`apps/common/serializers.py:41`) y `MeSerializer.perfiles`; contrato del frontend en
  `docs/api_accesos_frontend.md` §1 (`{tipo_entidad, id_objeto, entidad, rol}`).
- **Enforcement del scope ya existente (consumidores de T10):** `HasEntityScope`, `exigir_ambito`,
  `IsInstitutionalMember` (`apps/common/permissions.py`); `perfiles_del_usuario`, `entidades_del_usuario`,
  `usuario_pertenece_a_entidad` (`apps/common/selectors.py`).
- **Permisos:** patrón en `apps/common/permissions.py` (`IsInstitutionalMember`, `HasEntityScope`);
  nuevo `IsSuperUser` aquí.
- **Auditoría:** `registrar_auditoria` (`apps/common/services.py:9`) — escribe en `bitacora_auditoria`
  con cualquier modelo vía `ContentType` (incluye `User`/`Group`/`UserEntityProfile`).
- **Patrón de ViewSets/auditoría:** `AuditedModelViewSet`, read/write serializers y `@action`
  (`apps/convenios/views.py`). En esta feature se replica el comportamiento de auditoría **sin importar
  desde `convenios.views`** (mantener `common` como base; ver T5). Importar el **modelo**
  `UserEntityProfile` desde `apps.convenios.models` sí está permitido (patrón ya existente).
- **RN:** RN-20 (registro por universidad con alcance, 1..N), RN-22 (onboarding del interno: perfil sobre
  `Student`). **RNF:** RNF-SEG-01/02/03 (autorización por rol/superusuario, anti-escalación),
  RNF-AUD-01/02 (bitácora de operaciones críticas).

## Fuera de alcance (este spec)

Tests automatizados; modelos/migraciones nuevos; endpoint de login nuevo (se enriquece el existente);
recuperación de contraseña por email / flujos de auto-registro; cambios al núcleo de los módulos ya
validados. **T11 no** incluye entidades de la app `actividades` en la allowlist (no hay rol con alcance
por actividad); si se requiere, se decide en spec posterior.

> **Nota (corrección):** la escritura de perfiles institucionales (`UserEntityProfile`) **entra en
> alcance** en este spec (ver **T10**). La versión anterior de este documento la daba por "fuera de
> alcance, ya cubierta en `convenios` por `IsAdminRole`", lo cual **no era exacto**: en `convenios` solo
> existe el **enforcement/lectura** del scope (`HasEntityScope`, `perfiles_del_usuario`, `MeSerializer`),
> pero **no había un endpoint de escritura** para otorgar/revocar el vínculo usuario↔entidad. T10 cubre
> ese hueco como sub-recurso de usuarios en `apps/common`, restringido a `IsSuperUser`. **T11** añade el
> lookup que destraba el alta de perfiles en el frontend y unifica la allowlist con la validación de T10.
