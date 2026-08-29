# Spec — Feature "Calendario de actividades administrativas"

> **App nueva:** `apps/calendario` (`AppConfig.label = "calendario"`).
> **Metodología:** SDD. Este documento es la lista exacta de tareas para el agente `implement`. **No** contiene código de aplicación.
> **Fuentes de verdad:** `docs/arquitectura_desarrollo.md` (capas), `docs/alcance_mvp.md`, `CLAUDE.md`, los `docs/db_schema_*.md`, y los archivos citados en cada tarea.

---

## 1. Resumen del módulo

El **Calendario de actividades administrativas** permite al `Administrador RENADS` definir "actividades" (hitos/ventanas) que, además de servir como agenda informativa, pueden **habilitar o bloquear la escritura** de módulos funcionales de RENADS durante una ventana de fechas.

Ejemplo de uso: "Registro de internos" abierto del 01/03 al 31/03; fuera de esa ventana, ningún usuario (salvo `Administrador RENADS`/superusuario) puede crear/editar internados.

### Entidades que cubre

| Entidad (clase Python) | Tabla | Rol |
|---|---|---|
| `CalendarActivity` | `actividad_calendario` | Actividad/hito de calendario, opcionalmente controladora de acceso a uno o varios módulos (ContentType). |
| Tabla puente `responsables` | (español, ver T2) | M2M `CalendarActivity` → `auth.Group` (roles responsables de la actividad). |
| Tabla puente `content_types` | (español, ver T2) | M2M `CalendarActivity` → `contenttypes.ContentType` (módulos/modelos que la actividad referencia y, si `controla_acceso=True`, gobierna). |

### Decisiones cerradas (contrato — no reabrir)

Cada decisión se **verifica** en las tareas indicadas:

| Decisión | Valor | Tarea |
|---|---|---|
| Nombre de tabla del modelo principal | `actividad_calendario` (evita colisión con módulo `actividades`) | T2 |
| `numero_orden` | `PositiveIntegerField`, **NO unique**, usado como `ordering` por defecto | T2, T5 |
| `fecha_fin` | `DateField(null=True)`; **NULL = ventana abierta** (sin cierre) | T2, T4 |
| Granularidad del gate | por **modelo**, vía `ContentType` `(app_label, model)` | T4, T7 |
| Ámbito del gate temporal | **solo métodos de escritura** (`create`/`update`/`partial_update`/`destroy`); la lectura queda libre | T7 |
| Exentos del gate temporal | **superusuario** y rol `Administrador RENADS` | T7 |
| Semántica entre ventanas | **OR**: un CT está habilitado si tiene ≥1 ventana activa hoy | T4 |
| Cálculo en `/auth/me/` | **siempre** (2 queries), para `now` = fecha/hora del request | T8 |
| Escritura del CRUD `calendar-activities` | solo `Administrador RENADS` (`IsAdminRoleOrReadOnly`); lectura autenticados | T5 |
| Endpoint `content-types` | read-only, `IsAuthenticated`, en `apps/common` | T6 |
| Instrumentación opt-in | 3 viewsets exactos (T9); pass-through si la vista no declara `module_content_type` | T7, T9 |

---

## 2. Tareas por capa

Convenciones (recordatorio de `CLAUDE.md`): código/identificadores en **inglés**; tablas, columnas y `help_text`/`verbose_name` en **español**; comentarios/docstrings en **español**. Activar `.venv\Scripts\Activate.ps1` antes de `makemigrations`/`migrate`. **No** ejecutar `runserver`.

---

### T1 — Crear la app `apps/calendario` y registrarla

**Acciones:**
1. Crear el paquete `apps/calendario/` con: `__init__.py`, `apps.py`, `models.py`, `serializers.py`, `services.py` (si aplica), `selectors.py`, `filters.py`, `permissions.py` (opcional), `views.py`, `urls.py`, `migrations/__init__.py`. (No crear `tests.py`: testing fuera de alcance MVP.)
2. En `apps.py`: `class CalendarioConfig(AppConfig)` con `default_auto_field = "django.db.models.BigAutoField"`, `name = "apps.calendario"` y **`label = "calendario"`** (imitar el patrón de las demás apps: ver `apps/actividades/apps.py`).
3. Registrar `"apps.calendario"` en `INSTALLED_APPS` de `config/settings/base.py` (líneas 32-35, tras `"apps.actividades"`).

**Criterios de aceptación:**
- `python manage.py check` pasa sin errores.
- `apps.calendario` aparece en `INSTALLED_APPS`; el `app_label` efectivo es `calendario`.
- No hay colisión de `db_table` con la app `actividades`.

**Referencias:** `config/settings/base.py:18-35`, `apps/actividades/apps.py`.

---

### T2 — Modelo `CalendarActivity` + M2M `responsables` y `content_types`

**Acciones:** en `apps/calendario/models.py` definir `class CalendarActivity(models.Model)` con `Meta.db_table = "actividad_calendario"`, `Meta.verbose_name = "actividad de calendario"`, `Meta.ordering = ["numero_orden", "id"]`.

Campos (todos con `help_text` en español; los `verbose_name` van en español como primer argumento posicional donde aplique — mismo estilo que `apps/actividades/models.py`):

| Campo (inglés) | Tipo Django | Restricciones | Notas |
|---|---|---|---|
| `nombre` | `CharField(max_length=...)` | requerido | Nombre de la actividad. |
| `detalle` | `TextField(blank=True)` | opcional | Descripción/detalle. |
| `numero_orden` | `PositiveIntegerField(default=0)` | **NO unique** | Orden de presentación; usado en `Meta.ordering`. |
| `fecha_inicio` | `DateField()` | requerido | Inicio de la ventana. |
| `fecha_fin` | `DateField(null=True, blank=True)` | opcional | **NULL = ventana abierta** (sin fecha de cierre). `help_text` debe decirlo. |
| `controla_acceso` | `BooleanField(default=False)` | — | Si `True`, la actividad gobierna la escritura de sus `content_types`. |
| `activo` | `BooleanField(default=True)` | — | Baja lógica / activación. |
| `creado_en` | `DateTimeField(auto_now_add=True)` | — | Auditoría. |
| `creado_por` | `FK(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+", null=True, blank=True)` | — | Auditoría. |
| `actualizado_en` | `DateTimeField(auto_now=True)` | — | Auditoría. |
| `actualizado_por` | `FK(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+", null=True, blank=True)` | — | Auditoría. |

M2M (con tabla puente **en español, sin verbos**):
- `responsables = models.ManyToManyField("auth.Group", db_table="actividad_calendario_responsable", blank=True, related_name="actividades_calendario_responsable", help_text="Roles responsables de la actividad")`.
- `content_types = models.ManyToManyField("contenttypes.ContentType", db_table="actividad_calendario_content_type", blank=True, related_name="+", help_text="Módulos/modelos que la actividad referencia y, si controla_acceso=True, gobierna")`.

**Criterios de aceptación:**
- `makemigrations calendario` genera la migración inicial; `migrate` la aplica sin error.
- La tabla se llama `actividad_calendario`; las puentes `actividad_calendario_responsable` y `actividad_calendario_content_type`.
- `numero_orden` NO tiene `unique=True` (verificable en la migración).
- `fecha_fin` admite `NULL`; su `help_text` documenta "NULL = ventana abierta".
- `Meta.ordering == ["numero_orden", "id"]`.

**Referencias:** patrón de auditoría/estilo en `apps/actividades/models.py:34-73`; `db_schema` a crear en T13.

---

### T3 — Serializers read/write de `CalendarActivity`

**Acciones:** en `apps/calendario/serializers.py`:
1. `CalendarActivityWriteSerializer` (`ModelSerializer`): recibe escritura, incluye `responsables` y `content_types` como `PrimaryKeyRelatedField(many=True)` (ids). Campos de auditoría (`creado_por`/`actualizado_por`/`creado_en`/`actualizado_en`) **read-only** o excluidos de la escritura.
2. `CalendarActivityReadSerializer` (`ModelSerializer`): expone todos los campos legibles **más**:
   - `responsables_detalle`: lista `{id, name}` (usar `GroupBriefSerializer` de `apps/common/serializers.py` o `SerializerMethodField`).
   - `content_types_detalle`: lista `{id, app_label, model, verbose_name}` por cada ContentType (mismo shape que el endpoint `content-types` de T6; `verbose_name` = `ct.model_class()._meta.verbose_name` con fallback a `ct.name` si `model_class()` es `None`).
3. **Validación de serializer (RN, no de service):** `fecha_fin`, si se envía no nula, debe ser `>= fecha_inicio` → error en español si no. (Ventana abierta = `fecha_fin` nula, permitida.)

**Criterios de aceptación:**
- El write acepta `responsables: [id]` y `content_types: [id]` y persiste ambos M2M.
- El read devuelve `responsables_detalle` y `content_types_detalle` con el shape especificado.
- Enviar `fecha_fin < fecha_inicio` devuelve `400` con mensaje en español; enviar `fecha_fin` nula es válido.

**Referencias:** `apps/common/serializers.py:91-96` (`GroupBriefSerializer`); patrón read/write en `apps/convenios/serializers.py` (Convention read/write).

---

### T4 — Selector de habilitación (fuente única temporal) en `apps/calendario/selectors.py`

**Acciones:** implementar 3 funciones puras (sin efectos), tomando `now` como parámetro (fecha/hora; se usará su parte `date` para comparar con `DateField`). La semántica entre ventanas es **OR**.

1. `content_types_controlados(now) -> set[int]`
   - Conjunto de `content_type_id` referenciados por alguna `CalendarActivity` con `controla_acceso=True` **y** `activo=True`. (No filtra por fechas: define "quién está gobernado".)
2. `content_types_habilitados(now) -> set[int]`
   - Subconjunto de los controlados que tiene **≥1 ventana activa hoy**: existe una `CalendarActivity` con `controla_acceso=True`, `activo=True`, `fecha_inicio <= now.date()` **y** (`fecha_fin` es NULL **o** `fecha_fin >= now.date()`). NULL = ventana abierta.
3. `esta_habilitado(ct_id, now) -> bool`
   - `True` si `ct_id` **no** está en `content_types_controlados(now)` (módulo no gobernado ⇒ siempre libre), **o** si está en `content_types_habilitados(now)`.

**Criterios de aceptación:**
- Módulo sin actividad controladora ⇒ `esta_habilitado` = `True` (pass-through).
- Módulo controlado con ventana `fecha_inicio<=hoy` y `fecha_fin` NULL ⇒ habilitado.
- Módulo controlado con ventana ya cerrada (`fecha_fin < hoy`) y sin otra ventana vigente ⇒ **no** habilitado.
- Dos ventanas sobre el mismo CT: basta una vigente para habilitar (OR).
- Actividad con `activo=False` o `controla_acceso=False` no aporta control ni habilitación.
- `content_types_habilitados ⊆ content_types_controlados` para el mismo `now`.

**Referencias:** patrón de selectores en `apps/common/selectors.py`; `docs/arquitectura_desarrollo.md` (capa `selectors`).

---

### T5 — ViewSet CRUD `calendar-activities`

**Acciones:** en `apps/calendario/views.py`:
1. `CalendarActivityViewSet(AuditedModelViewSet)` — importar `AuditedModelViewSet` desde `apps/convenios/views.py` (reutilización ya usada por otras apps).
2. `permission_classes = [IsAuthenticated, IsAdminRoleOrReadOnly]` (import `IsAdminRoleOrReadOnly` de `apps/convenios/permissions.py`). Escritura solo superusuario/`Administrador RENADS`; lectura autenticados.
3. `get_serializer_class`: `CalendarActivityReadSerializer` en `list`/`retrieve`; `CalendarActivityWriteSerializer` en el resto.
4. `queryset`: `CalendarActivity.objects.prefetch_related("responsables", "content_types").all()`; `ordering = ["numero_orden", "id"]`.
5. `filterset_class = CalendarActivityFilter` (T10).
6. Auditoría: fijar `creado_por`/`actualizado_por` con `self.request.user` en `perform_create`/`perform_update` (además de la auditoría en `bitacora_auditoria` que ya aporta `AuditedModelViewSet`).
7. **No** aplicar `IsModuleEnabled` a este viewset (el propio calendario no se gatea).

**Criterios de aceptación:**
- `GET /api/v1/calendar-activities/` accesible a cualquier autenticado; ordenado por `numero_orden` asc.
- `POST/PATCH/PUT/DELETE` denegados (`403`) a usuarios sin rol `Administrador RENADS`; permitidos a superusuario y `Administrador RENADS`.
- `creado_por`/`actualizado_por` quedan seteados con el usuario del request.
- Cada operación de escritura registra fila en `bitacora_auditoria`.

**Referencias:** `apps/convenios/views.py:195-228` (`AuditedModelViewSet`, `ConventionTemplateViewSet`), `apps/convenios/permissions.py:36-47`.

---

### T6 — Endpoint read-only `content-types` en `apps/common`

**Acciones:** en `apps/common/views.py` crear `ContentTypeListView(APIView)` imitando `SolicitanteContentTypeView` de `apps/convenios/views.py:715-744`:
1. `permission_classes = [IsAuthenticated]`.
2. `GET` devuelve la lista de ContentTypes con `{id, app_label, model, verbose_name}`.
   - `verbose_name`: `ct.model_class()._meta.verbose_name` con fallback a `ct.name` cuando `model_class()` sea `None` (CT huérfano).
   - Ordenar por `app_label`, `model` (o por `id`, consistente con el precedente que ordena por `id`).
3. Serializer de salida `ContentTypeSerializer(serializers.Serializer)` con los 4 campos (en `apps/common/serializers.py`), anotado con `@extend_schema`/`extend_schema_field` para OpenAPI.
4. Registrar la ruta en `apps/common/urls.py` como `path("content-types/", ContentTypeListView.as_view(), name="content-types")`.

**Alcance:** el frontend usa esta lista para poblar el selector `content_types[]` del CRUD de `calendar-activities` y para interpretar `modulos_habilitados`/`modulos_bloqueados` de `/auth/me/`.

**Criterios de aceptación:**
- `GET /api/v1/content-types/` responde `200` a autenticados; cada item trae `id`, `app_label`, `model`, `verbose_name`.
- Aparece en el schema OpenAPI (`/api/v1/schema/`).

**Referencias:** `apps/convenios/views.py:715-744`, `apps/common/urls.py:19-26`.

---

### T7 — Permission class reutilizable `IsModuleEnabled`

**Acciones:** en `apps/common/permissions.py` añadir `class IsModuleEnabled(BasePermission)`:
1. **Opt-in por atributo de vista:** lee `module_content_type = (app_label, model)` de la vista. Si la vista **no** lo declara (`None`/ausente) ⇒ `has_permission` devuelve `True` (**pass-through**, sin efecto).
2. **Solo gatea escritura:** si `request.method in SAFE_METHODS` ⇒ `True` (lectura libre).
3. **Exentos:** si `request.user.is_superuser` o pertenece al grupo `Administrador RENADS` ⇒ `True`.
4. **Enforcement:** resolver el `ContentType` desde `(app_label, model)` (`ContentType.objects.get_by_natural_key(app_label, model)`); consultar `esta_habilitado(ct.id, now=timezone.now())` mediante **import lazy** del selector de calendario (importar dentro del método, **no** a nivel de módulo, para evitar ciclo `common` ↔ `calendario` — mismo patrón que `IsInstitutionalMember` en `apps/common/permissions.py:53`). Si no está habilitado ⇒ denegar.
5. **Formato de error estándar:** denegar con `codigo = "MODULO_FUERA_DE_VENTANA"` y mensaje en español (p. ej. "El módulo está fuera de su ventana de registro."). Usar el mismo mecanismo de error que el resto del proyecto (lanzar `PermissionDenied` con el detalle/estructura que produzca `codigo="MODULO_FUERA_DE_VENTANA"`; verificar el handler de excepciones vigente en `config/settings` para respetar el shape estándar).

**Criterios de aceptación:**
- Vista sin `module_content_type` ⇒ el permiso nunca bloquea (pass-through), en lectura y escritura.
- `GET`/`HEAD`/`OPTIONS` nunca bloqueados aunque el módulo esté fuera de ventana.
- Superusuario y `Administrador RENADS` pueden escribir aunque el módulo esté fuera de ventana.
- Usuario normal con módulo controlado y fuera de ventana ⇒ `403` con `codigo="MODULO_FUERA_DE_VENTANA"`.
- Usuario normal con módulo controlado y dentro de ventana (o módulo no controlado) ⇒ escritura permitida.
- No hay import de `apps.calendario` a nivel de módulo en `apps/common/permissions.py` (import dentro del método).

**Referencias:** `apps/common/permissions.py:39-55` (patrón import lazy de `IsInstitutionalMember`), `apps/convenios/permissions.py:15-16` (detección `Administrador RENADS`).

---

### T8 — `/auth/me/`: `modulos_habilitados` y `modulos_bloqueados`

**Acciones:**
1. En `MeSerializer` (`apps/common/serializers.py:54-76`) añadir dos campos `SerializerMethodField`:
   - `modulos_habilitados`: lista de `{app_label, model, content_type_id}` de los CT que están **habilitados** para escribir por el usuario **según el selector** para `now = timezone.now()`.
   - `modulos_bloqueados`: lista de `{app_label, model, content_type_id}` de los CT **controlados** pero **no** habilitados.
2. Derivarlos del **mismo** selector de T4: `controlados = content_types_controlados(now)`, `habilitados = content_types_habilitados(now)`; `bloqueados = controlados - habilitados`. Resolver `app_label`/`model` con una consulta a `ContentType` por los ids. **Total 2 queries** (una del selector agregado + una para resolver metadatos de los CT involucrados). Import del selector puede ser a nivel de módulo en `serializers.py` (no hay ciclo con `calendario` desde ahí) o lazy; preferir lazy si aparece cualquier ciclo.
3. **Calcular siempre**, con independencia de si el usuario es admin (para admin, todos los controlados podrían listarse como habilitados según la semántica; documentar el criterio elegido: los campos reflejan el **estado temporal del módulo**, no la exención del admin — es decir, para admin/superuser `modulos_bloqueados` sí puede listar módulos fuera de ventana, aunque el gate no los bloquee; documentar esta interpretación en el docstring y en `docs/api_accesos_frontend.md`).

**Criterios de aceptación:**
- `GET /api/v1/auth/me/` incluye `modulos_habilitados` y `modulos_bloqueados`, cada uno lista de `{app_label, model, content_type_id}`.
- Los valores coinciden con lo que devuelve el selector de T4 para el mismo instante.
- La resolución no dispara N+1 (≈2 queries para estos campos).
- Sin actividades controladoras: `modulos_habilitados == []` y `modulos_bloqueados == []`.

**Referencias:** `apps/common/serializers.py:54-76`, `apps/common/views.py:41-48`.

---

### T9 — Instrumentar (opt-in) los 3 viewsets funcionales

Añadir a cada uno: atributo `module_content_type = (app_label, model)` y `IsModuleEnabled` en `permission_classes` (append, sin quitar permisos existentes). **No-op** hasta que exista una `CalendarActivity` controladora de ese CT.

| # | Viewset | Archivo | `module_content_type` |
|---|---|---|---|
| 9a | `ConventionViewSet` | `apps/convenios/views.py:60-63` | `("convenios", "convention")` |
| 9b | `InternshipViewSet` | `apps/internados/views.py:42` | `("internados", "internship")` |
| 9c | **`TeachingActivityViewSet`** | `apps/actividades/views.py:30-33` | `("actividades", "teachingactivity")` |

> **Corrección verificada:** el enunciado mencionaba tentativamente `ActivityViewSet` para `apps/actividades`. El viewset real es **`TeachingActivityViewSet`** y su modelo principal es **`TeachingActivity`** (`apps/actividades/models.py:34`, `db_table="actividad_docente_asistencial"`). El ContentType correcto es `("actividades", "teachingactivity")`. Confirmar el `model` en minúscula del CT (`TeachingActivity` ⇒ `teachingactivity`).

**Acciones adicionales:**
- Importar `IsModuleEnabled` desde `apps.common.permissions` en cada `views.py`.
- `permission_classes` resultantes (append al final):
  - `ConventionViewSet`: `[IsAuthenticated, IsInstitutionalMember, ConventionScope, IsModuleEnabled]`.
  - `InternshipViewSet`: su lista actual + `IsModuleEnabled`.
  - `TeachingActivityViewSet`: `[IsAuthenticated, IsInstitutionalMember, ActivityScope, IsModuleEnabled]`.
- **No** instrumentar: catálogos, entidades CRUD genéricas, auth, `content-types`, ni `calendar-activities`.

**Criterios de aceptación:**
- Sin actividad controladora para el CT correspondiente ⇒ comportamiento idéntico al actual (no-op) en los 3 endpoints.
- Con actividad controladora `controla_acceso=True, activo=True` cuya ventana **no** incluye hoy ⇒ usuario normal recibe `403 MODULO_FUERA_DE_VENTANA` al crear/editar/borrar en ese endpoint; lectura sigue disponible; admin/superuser pueden escribir.
- Ningún otro endpoint cambia de comportamiento.

**Referencias:** `apps/convenios/views.py:60-63`, `apps/internados/views.py:42`, `apps/actividades/views.py:30-33 y :121-126`, `apps/actividades/models.py:34-73`.

---

### T10 — Filters (django-filter) de `calendar-activities`

**Acciones:** en `apps/calendario/filters.py` crear `CalendarActivityFilter(FilterSet)` con:
- `controla_acceso` (boolean exacto).
- `activo` (boolean exacto).
- `content_types` (filtro por id de ContentType relacionado; permitir múltiples).
- Rango de fechas: filtros sobre la ventana — al menos `fecha_inicio` (`gte`/`lte`) y `fecha_fin` (`gte`/`lte`), p. ej. `fecha_desde`/`fecha_hasta`. Definir nombres explícitos y documentarlos.

**Criterios de aceptación:**
- `?controla_acceso=true`, `?activo=false`, `?content_types=<id>` y los filtros de rango de fecha funcionan y son combinables.
- `CalendarActivityFilter` está enlazado en `CalendarActivityViewSet.filterset_class`.

**Referencias:** patrón `ConventionFilter` en `apps/convenios/filters.py`; `docs/arquitectura_desarrollo.md` (capa `filters`).

---

### T11 — URLs / router del módulo y registro en `/api/v1/`

**Acciones:**
1. En `apps/calendario/urls.py`: `DefaultRouter`, `router.register("calendar-activities", CalendarActivityViewSet, basename="calendar-activity")`; exportar `urlpatterns` (mismo patrón que `apps/convenios/urls.py`).
2. En `config/api_urls.py`, agregar `path("", include("apps.calendario.urls"))` dentro del bloque "Módulos" (tras la línea 31).
3. `content-types` se expone vía `apps/common/urls.py` (T6), ya incluido en `config/api_urls.py:33`.

**Criterios de aceptación:**
- `GET /api/v1/calendar-activities/` resuelve.
- `GET /api/v1/content-types/` resuelve.
- `python manage.py check` sin errores; ambas rutas aparecen en `/api/v1/schema/`.

**Referencias:** `apps/convenios/urls.py`, `apps/common/urls.py`, `config/api_urls.py:28-34`.

---

### T12 — Permissions (resumen y ubicación)

- Escritura de `calendar-activities`: `IsAdminRoleOrReadOnly` (reutilizada de `apps/convenios/permissions.py`).
- Gate temporal transversal: `IsModuleEnabled` (nueva, en `apps/common/permissions.py`, T7).
- `content-types`: `IsAuthenticated`.
- **No** se crean permisos con alcance institucional para el calendario (es configuración global de admin).

**Criterio de aceptación:** ninguna clase de permiso nueva vive fuera de `apps/common/permissions.py`; el CRUD reutiliza las de convenios sin duplicarlas.

---

### T13 — Documentación (obligatoria, en el mismo cambio)

1. **`docs/db_schema_modulo_04_calendario.md`** (número libre verificado: existen 01, 02, 03 ⇒ **04**). Incluir: contexto, tabla `actividad_calendario` con todas las columnas/tipos/descripciones en español, las 2 tablas puente, y la nota "fecha_fin NULL = ventana abierta" + "numero_orden no unique".
2. **`docs/db_schema_er_global.md`**: agregar `actividad_calendario` y sus puentes al diagrama/listado global, con relaciones a `auth_group` y `django_content_type`.
3. **`CLAUDE.md`**: (a) nueva fila en la tabla de módulos (M4 — Calendario / app `calendario` / nuevo doc); (b) sección con el **contrato de enforcement** (`IsModuleEnabled`, opt-in por `module_content_type`, solo escritura, admin/superuser exentos, OR entre ventanas, `fecha_fin` NULL = abierta, granularidad por ContentType); (c) nueva **RN** (numerar consecutiva a las existentes, p. ej. **RN-25 (ventana habilita escritura de módulo)**) describiendo la regla y sus exentos.
4. **`docs/alcance_mvp.md`**: incorporar el feature Calendario al alcance.
5. **`docs/api_accesos_frontend.md`**: documentar `content-types`, el CRUD `calendar-activities` (write con `responsables[]`/`content_types[]` por id; read con `*_detalle`), y los nuevos campos `modulos_habilitados`/`modulos_bloqueados` de `/auth/me/` (shape `{app_label, model, content_type_id}` + criterio para admin/superuser de T8).

**Criterios de aceptación:**
- Los 5 documentos quedan actualizados y coherentes con los modelos/endpoints implementados.
- El nombre del nuevo doc es exactamente `docs/db_schema_modulo_04_calendario.md`.
- La nueva RN queda numerada sin colisionar con las existentes en `CLAUDE.md`.

---

### T14 — Migraciones y verificación

**Acciones:** activar `.venv`, `python manage.py makemigrations calendario`, `python manage.py migrate`, `python manage.py check`.

**Criterios de aceptación:** las 3 órdenes terminan sin error; la migración inicial de `calendario` crea `actividad_calendario` + puentes; no se generan migraciones inesperadas en `convenios`/`internados`/`actividades`/`common` por los cambios (los cambios de permission_classes y serializers no producen migraciones).

---

### T15 — Cierre: `/code-review`

**Acción:** ejecutar la skill **`/code-review`** sobre todo el cambio (modelos, serializers, views, permissions, filters, urls, migración) antes de dar por terminada la implementación (obligatorio por `CLAUDE.md`).

**Criterio de aceptación:** `/code-review` ejecutada; observaciones resueltas o justificadas.

---

## 3. Reglas de negocio: dónde vive cada validación

| Regla | Ubicación | Tarea |
|---|---|---|
| `fecha_fin >= fecha_inicio` (si `fecha_fin` no nula) | **Serializer** (`CalendarActivityWriteSerializer.validate`) | T3 |
| `fecha_fin` NULL = ventana abierta | Modelo (`null=True`) + selector (comparación) | T2, T4 |
| Habilitación por ventana (OR, granularidad ContentType) | **Selector** (fuente única temporal) | T4 |
| Gate de escritura (solo escritura, admin/superuser exentos, pass-through sin `module_content_type`) | **Permission** `IsModuleEnabled` | T7 |
| Escritura del CRUD solo `Administrador RENADS` | **Permission** `IsAdminRoleOrReadOnly` | T5 |
| Exposición de estado de módulos al front | **Serializer** `MeSerializer` (deriva del selector) | T8 |

> El selector de T4 es la **fuente única** de la semántica temporal: tanto `IsModuleEnabled` (T7) como `MeSerializer` (T8) la consumen; no duplicar la lógica de fechas en ningún otro lugar.

---

## 4. Referencias de código (fuentes de verdad revisadas)

- `apps/common/permissions.py:39-55` — patrón import lazy (`IsInstitutionalMember`); `IsSuperUser`, `exigir_ambito`, `HasEntityScope`.
- `apps/convenios/permissions.py:15-16, 36-47, 103-112` — detección `Administrador RENADS`, `IsAdminRoleOrReadOnly`, `exigir_roles`.
- `apps/convenios/views.py:60-63` (ConventionViewSet permisos), `:195-228` (`AuditedModelViewSet`, `ConventionTemplateViewSet`), `:715-744` (`SolicitanteContentTypeView`).
- `apps/common/views.py:41-48` (`MeView`), `apps/common/serializers.py:54-76` (`MeSerializer`), `:91-96` (`GroupBriefSerializer`).
- `apps/internados/views.py:42` (`InternshipViewSet`).
- `apps/actividades/views.py:30-33, 121-126` (`TeachingActivityViewSet`); `apps/actividades/models.py:34-73` (`TeachingActivity`, CT `actividades.teachingactivity`).
- `config/settings/base.py:18-35` (`INSTALLED_APPS`), `config/api_urls.py:28-34` (router de módulos), `apps/convenios/urls.py`, `apps/common/urls.py:19-26`.
- `apps/common/selectors.py` (patrón de selectores).
- Schemas existentes: `docs/db_schema_modulo_03_actividades.md` (formato de referencia para el nuevo doc 04).
