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

**Entidades cubiertas:** `User` (tabla `auth_user`), `Group` (`auth_group`), `Permission`
(`auth_permission`), más las M2M `auth_user_groups` y `auth_group_permissions`.

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

## Verificación (cierre)

1. `python manage.py check` sin errores (activar antes `.venv\Scripts\Activate.ps1`).
2. `python manage.py makemigrations` **no** debe generar migraciones nuevas (no se crean modelos).
3. `python manage.py spectacular --file schema.yml` (o `/api/schema/`) genera sin error e incluye los
   paths `users`, `groups`, `permissions`.
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
   - Verificar registros `CREAR`/`ACTUALIZAR`/`DESACTIVAR` de usuarios y `CREAR`/`ACTUALIZAR`/`ELIMINAR`
     de grupos en `bitacora_auditoria`.

## Endpoints resultantes

| Método(s) | Endpoint | ViewSet | Permisos |
|-----------|----------|---------|----------|
| POST | `/api/v1/auth/token/` | `CustomTokenObtainPairView` (enriquecido) | público (credenciales) |
| GET / POST | `/api/v1/users/` | `UserViewSet` | `IsSuperUser` |
| GET / PUT / PATCH / DELETE | `/api/v1/users/{id}/` | `UserViewSet` (DELETE = desactivar) | `IsSuperUser` |
| POST | `/api/v1/users/{id}/set-password/` | `UserViewSet` (action) | `IsSuperUser` |
| GET / POST | `/api/v1/groups/` | `GroupViewSet` | `IsSuperUser` |
| GET / PUT / PATCH / DELETE | `/api/v1/groups/{id}/` | `GroupViewSet` | `IsSuperUser` |
| GET | `/api/v1/permissions/` | `PermissionViewSet` | `IsSuperUser` |
| GET | `/api/v1/permissions/{id}/` | `PermissionViewSet` | `IsSuperUser` |

## Referencias

- **Modelos nativos Django:** `django.contrib.auth.models.User` (`auth_user`), `Group` (`auth_group`),
  `Permission` (`auth_permission`), M2M `auth_user_groups` / `auth_group_permissions`. No inventar
  campos: usar los del modelo estándar.
- **Auth existente:** `CustomTokenObtainPairSerializer` y `MeSerializer`
  (`apps/common/serializers.py`); `CustomTokenObtainPairView`/`MeView` (`apps/common/views.py`); rutas
  en `config/api_urls.py`.
- **Permisos:** patrón en `apps/common/permissions.py` (`IsInstitutionalMember`, `HasEntityScope`);
  nuevo `IsSuperUser` aquí.
- **Auditoría:** `registrar_auditoria` (`apps/common/services.py:9`) — escribe en `bitacora_auditoria`
  con cualquier modelo vía `ContentType` (incluye `User`/`Group`).
- **Patrón de ViewSets/auditoría:** `AuditedModelViewSet`, read/write serializers y `@action`
  (`apps/convenios/views.py`). En esta feature se replica el comportamiento de auditoría **sin importar
  desde `convenios`** (mantener `common` como base; ver T5).
- **RNF:** RNF-SEG-01/02/03 (autorización por rol/superusuario, anti-escalación), RNF-AUD-01/02
  (bitácora de operaciones críticas).

## Fuera de alcance (este spec)

Tests automatizados; modelos/migraciones nuevos; endpoint de login nuevo (se enriquece el existente);
recuperación de contraseña por email / flujos de auto-registro; gestión de perfiles institucionales
(`UserEntityProfile`, ya cubierta en `convenios` por `IsAdminRole`); cambios al núcleo de los módulos ya
validados.
