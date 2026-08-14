# Esquema de Base de Datos — Módulo 4: Calendario de actividades administrativas (RENADS)

## Contexto y alcance

El módulo **Calendario de actividades administrativas** modela una agenda de hitos/ventanas del proceso RENADS y, además, **gobierna la habilitación temporal de la escritura** de uno o varios módulos funcionales. Una `CalendarActivity` (tabla `actividad_calendario`) es un hito con una **ventana de fechas** (`fecha_inicio`..`fecha_fin`) que, cuando `controla_acceso = True`, **habilita o bloquea la escritura** (`POST`/`PUT`/`PATCH`/`DELETE`) de los modelos que referencia (vía `django_content_type`) mientras la ventana esté vigente.

La feature vive en la app **`apps.calendario`** (clases en inglés; tablas, columnas y descripciones en español).

### Reglas de negocio clave (validación / enforcement a nivel de aplicación)

- **La ventana habilita** (RN-26): una `CalendarActivity` con `controla_acceso = True` y `activo = True` gobierna la escritura de sus `content_types`. La escritura de un módulo gobernado se permite **solo** si existe al menos una ventana vigente en el instante actual.
- **`fecha_fin` NULL = ventana abierta** (sin fecha de cierre): la ventana se considera vigente indefinidamente desde `fecha_inicio`.
- **Semántica OR entre ventanas** del mismo `ContentType`: basta **una** actividad controladora con ventana vigente para habilitar el módulo.
- **Opt-in por módulo:** solo se gobiernan los `ContentType` referenciados por alguna actividad controladora. Un módulo no referenciado nunca se bloquea (*pass-through*).
- **Exención:** el **superusuario** y el rol **`Administrador RENADS`** no son bloqueados por el gate de escritura (`IsModuleEnabled`), aunque el módulo esté fuera de ventana.
- **Coherencia de fechas:** si `fecha_fin` no es nula, debe ser `>= fecha_inicio` (validación del serializer de escritura).

> **Convenciones (heredadas de los módulos previos):** tablas/columnas/descripciones en **español**; se reutilizan tablas nativas de Django (`django_content_type` para los módulos gobernados) y la auditoría transversal.

---

## 1. Tablas reutilizadas

### Nativas de Django
| Tabla | Uso en el módulo 4 |
|-------|--------------------|
| `auth_user` | Auditoría (`creado_por`, `actualizado_por`) |
| `django_content_type` | Módulos/modelos **referenciados y gobernados** por la actividad (M2M) |

### Transversal (app `common`)
| Tabla | Uso en el módulo 4 |
|-------|--------------------|
| `bitacora_auditoria` | Auditoría de operaciones de escritura del CRUD de calendario |

---

## 2. Tabla principal

### `actividad_calendario` (`CalendarActivity`)

Hito/ventana del calendario administrativo. Sirve como agenda informativa y, si `controla_acceso = True`, gobierna la escritura de sus `content_types` durante la ventana `fecha_inicio`..`fecha_fin`.

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `nombre` | varchar(255) | No | Nombre de la actividad de calendario |
| `detalle` | text | No (`blank`) | Descripción o detalle de la actividad (puede ir vacío) |
| `responsables` | text | No (`blank`) | Responsables de la actividad (texto libre) |
| `numero_orden` | int positivo | No | Orden de presentación (default `0`; **no único**; usado en el ordenamiento por defecto) |
| `fecha_inicio` | date | No | Fecha de inicio de la ventana |
| `fecha_fin` | date | **Sí** | Fecha de fin de la ventana. **NULL = ventana abierta** (sin fecha de cierre) |
| `controla_acceso` | bool | No | Si es verdadero, la actividad gobierna la escritura de sus `content_types` (default `False`) |
| `activo` | bool | No | Activación / baja lógica de la actividad (default `True`) |
| `creado_en` | datetime | No | Marca de creación (`auto_now_add`) |
| `creado_por` | FK → `auth_user` | Sí | Usuario que creó la actividad (`db_column='creado_por'`, `PROTECT`) |
| `actualizado_en` | datetime | No | Marca de última actualización (`auto_now`) |
| `actualizado_por` | FK → `auth_user` | Sí | Usuario que actualizó por última vez (`db_column='actualizado_por'`, `PROTECT`) |

- **`Meta`:** `db_table = "actividad_calendario"`, `ordering = ["numero_orden", "id"]`.
- **`verbose_name`:** «actividad de calendario».

---

## 3. Tablas puente (M2M)

### `actividad_calendario_content_type` (M2M `CalendarActivity.content_types` → `django_content_type`)

Módulos/modelos que la actividad **referencia** y, si `controla_acceso = True`, **gobierna** (habilita/bloquea su escritura durante la ventana).

| Columna | Tipo | Null | Descripción |
|---------|------|------|-------------|
| `id` | PK | No | |
| `calendaractivity_id` | FK → `actividad_calendario` | No | Actividad |
| `contenttype_id` | FK → `django_content_type` | No | Módulo/modelo gobernado |

---

## 4. Reglas de enforcement (fuente única en `selectors.py`)

La semántica temporal es una **fuente única**: el selector `apps/calendario/selectors.py` calcula, para un instante `now`, qué módulos están gobernados y cuáles habilitados. Lo consumen el permiso de escritura `IsModuleEnabled` (`apps/common/permissions.py`) y la exposición al frontend `MeSerializer` (`apps/common/serializers.py`).

| Función del selector | Devuelve | Semántica |
|----------------------|----------|-----------|
| `content_types_controlados(now)` | `set[int]` | ContentTypes gobernados: referenciados por ≥1 actividad con `controla_acceso=True` y `activo=True`. **No** filtra por fechas. |
| `content_types_habilitados(now)` | `set[int]` | Subconjunto de los controlados con ≥1 **ventana vigente** en `now`: `activo=True`, `controla_acceso=True`, `fecha_inicio <= hoy` y (`fecha_fin` NULL **o** `fecha_fin >= hoy`). |
| `esta_habilitado(ct_id, now)` | `bool` | `True` si el módulo **no** está gobernado (*pass-through*) **o** tiene ventana vigente; `False` si está gobernado y sin ventana vigente. |

- **Ventana vigente:** `fecha_inicio <= hoy` **y** (`fecha_fin` es NULL **o** `fecha_fin >= hoy`). `hoy = now.date()`.
- **OR entre ventanas:** un ContentType queda habilitado si **cualquiera** de sus actividades controladoras tiene ventana vigente.
- **`fecha_fin` NULL:** ventana abierta (sin cierre) — vigente indefinidamente desde `fecha_inicio`.

### Gate de escritura — `IsModuleEnabled`

Permiso *opt-in* que instrumentan los ViewSets gobernados declarando el atributo de vista `module_content_type = (app_label, model)`:

- Si la vista **no** declara `module_content_type` ⇒ *pass-through* (nunca bloquea).
- Solo gatea métodos de **escritura**; la lectura (`SAFE_METHODS`) queda siempre libre.
- **Exentos:** superusuario y rol `Administrador RENADS`.
- En otro caso consulta `esta_habilitado(ct.id, now=timezone.now())`; si el módulo está fuera de ventana, deniega con **HTTP 403** y `code = "MODULO_FUERA_DE_VENTANA"` (mensaje: «El módulo está fuera de su ventana de registro.»).
- Si el `ContentType` no existe, no puede estar gobernado ⇒ *pass-through*.

**ViewSets instrumentados (a la fecha):** `ConventionViewSet` (M1), `InternshipViewSet` (M2), `TeachingActivityViewSet` (M3).

### Exposición al frontend — claims de `/auth/me/`

`MeSerializer` deriva del mismo selector y agrega dos campos a `GET /api/v1/auth/me/`:

- `modulos_habilitados`: lista de `{ app_label, model, content_type_id }` de los módulos gobernados con ventana vigente.
- `modulos_bloqueados`: lista de `{ app_label, model, content_type_id }` de los módulos gobernados **sin** ventana vigente.

> Estos campos reflejan el **estado temporal del módulo**, no la exención del admin: para admin/superusuario un módulo fuera de ventana aparece en `modulos_bloqueados` aunque `IsModuleEnabled` no lo bloquee.

---

## 5. Endpoints

| Recurso | Endpoint | Método(s) | Escritura | Lectura |
|---------|----------|-----------|-----------|---------|
| Tipos de contenido | `/api/v1/content-types/` | `GET` (list) | — (solo lectura) | Autenticados |
| Actividades de calendario | `/api/v1/calendar-activities/` | CRUD | Rol `Administrador RENADS` (con auditoría) | Autenticados |

- **`content-types`** expone `{ id, app_label, model, verbose_name }` — alimenta el selector `content_types[]` del CRUD de calendario y ayuda a interpretar `modulos_habilitados`/`modulos_bloqueados`.
- **`calendar-activities`** — lectura expone `content_types_detalle` (`[{id, app_label, model, verbose_name}]`); `responsables` es un campo de **texto libre** (string en lectura y escritura). Escritura recibe `content_types` por id. Filtros: `controla_acceso`, `activo`, `content_types` y rango de fechas.

---

## 6. Mapa app Django ↔ tablas

| App | Tablas (db_table) |
|-----|-------------------|
| **Calendario administrativo** (`calendario`, M4) | `actividad_calendario`, `actividad_calendario_content_type` (puente M2M → `django_content_type`) |
