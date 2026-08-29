# Validación — Feature "Calendario de actividades administrativas"

> Fecha: 2026-08-13 · Rama: `feat/almacenamiento-adjuntos`
> Resultado: **APROBADO (sin errores altos/medios).** Se generó la guía de pruebas manuales `spec/calendario.guia_pruebas.md`.
> Alcance de esta validación: **solo código** (T1–T12). Docs (T13), verificación de migración (T14) y `/code-review` (T15) quedan como **pendientes no bloqueantes** (se atienden aparte). Nota: aunque T14 no era objeto de esta revisión, se comprobó de todos modos que la migración está aplicada y `makemigrations --check` está limpio.

---

## 1. Comprobaciones ejecutadas (venv, sin `runserver`)

| Comprobación | Comando | Resultado |
|---|---|---|
| System check | `manage.py check` | `System check identified no issues (0 silenced).` |
| Migraciones pendientes | `manage.py makemigrations --check --dry-run` | `No changes detected` (no genera migraciones en calendario ni en otras apps). |
| Estado migración | `manage.py showmigrations calendario` | `[X] 0001_initial` aplicada. |
| Schema OpenAPI | `manage.py spectacular --validate` | **0 errores** (85 warnings, todos preexistentes en convenios/internados/actividades; ninguno de `calendario`). |
| Endpoints en schema | inspección de `schema.yml` | `/api/v1/calendar-activities/`, `/api/v1/content-types/` y `modulos_habilitados` presentes. |
| Rutas del router | resolución de URLconf | `calendar-activities` (+detalle/format) y `content-types/` resuelven bajo `/api/v1/`. |
| Imports / ciclos | importación directa de los 8 módulos de la app + `apps.common.permissions` | Sin ciclos `common ↔ calendario` (import lazy verificado). |

---

## 2. Cobertura del spec (T1–T12)

| Tarea | Estado | Nota |
|---|---|---|
| T1 — App `apps/calendario` + registro | OK | `CalendarioConfig.label = "calendario"`, registrada en `config/settings/base.py:36`, incluida en `config/api_urls.py:32`. |
| T2 — Modelo `CalendarActivity` + M2M | OK | `db_table="actividad_calendario"`; puentes `actividad_calendario_responsable` y `actividad_calendario_content_type`; `numero_orden` sin `unique`; `fecha_fin null=True` con help_text "NULL = ventana abierta"; `Meta.ordering=["numero_orden","id"]`. |
| T3 — Serializers read/write | OK | Write por ids (`responsables`/`content_types`); read con `responsables_detalle` (GroupBrief) y `content_types_detalle` (shape `{id, app_label, model, verbose_name}` con fallback a `ct.name`); validación `fecha_fin >= fecha_inicio` en `validate`. |
| T4 — Selector (fuente única temporal) | OK | `content_types_controlados`/`content_types_habilitados`/`esta_habilitado`; OR entre ventanas; `fecha_fin` NULL = abierta. Verificado por shell (pass-through, ventana abierta, ventana cerrada, OR, `activo=False`, subset invariant). |
| T5 — ViewSet CRUD `calendar-activities` | OK | `AuditedModelViewSet` + `[IsAuthenticated, IsAdminRoleOrReadOnly]`; read/write por acción; prefetch de M2M; **sin** `IsModuleEnabled`. |
| T6 — `content-types` read-only | OK | `ContentTypeListView` (`IsAuthenticated`) en `apps/common/views.py`; ruta en `apps/common/urls.py`; documentado con `@extend_schema`. |
| T7 — `IsModuleEnabled` | OK | Opt-in por `module_content_type`; pass-through si ausente; solo escritura; admin/superuser exentos; import lazy del selector; deniega con `code="MODULO_FUERA_DE_VENTANA"`. Verificado por shell. |
| T8 — `/auth/me/` módulos | OK | `modulos_habilitados`/`modulos_bloqueados` derivados del mismo selector; cache en instancia; para admin/superuser refleja estado temporal (bloqueados puede listar módulos fuera de ventana). |
| T9 — Instrumentar 3 viewsets | OK | Exactamente `ConventionViewSet` (`convenios.convention`), `InternshipViewSet` (`internados.internship`), `TeachingActivityViewSet` (`actividades.teachingactivity`). `IsModuleEnabled` al final de cada `permission_classes`. |
| T10 — Filters | OK | `controla_acceso`, `activo`, `content_types` (multi), `fecha_desde`/`fecha_hasta` (sobre `fecha_inicio`), `fecha_fin_desde`/`fecha_fin_hasta` (sobre `fecha_fin`); enlazado en `filterset_class`. |
| T11 — URLs / router | OK | `router.register("calendar-activities", ...)`; `content-types` vía `apps/common`; ambos bajo `/api/v1/`. |
| T12 — Permissions (ubicación) | OK | `IsModuleEnabled` en `apps/common/permissions.py`; CRUD reutiliza `IsAdminRoleOrReadOnly` de convenios sin duplicar. |

---

## 3. Enforcement — verificado por shell (transacción con rollback)

- Selector: sin actividad controladora ⇒ `esta_habilitado=True` (pass-through); ventana abierta (`fecha_fin` NULL) ⇒ habilitado; ventana cerrada sin otra vigente ⇒ no habilitado; **dos** ventanas sobre el mismo CT ⇒ basta una vigente (OR); `activo=False` no aporta control; `habilitados ⊆ controlados`.
- `IsModuleEnabled`: pass-through en vista sin `module_content_type`; `GET` (SAFE) libre aun fuera de ventana; superusuario y `Administrador RENADS` escriben fuera de ventana; usuario normal fuera de ventana ⇒ `403` con `code="MODULO_FUERA_DE_VENTANA"`; CT no controlado nunca gatea.
- `/auth/me/`: con un CT controlado fuera de ventana devolvió `modulos_habilitados=[]` y `modulos_bloqueados=[{app_label: convenios, model: convention, content_type_id}]`, coincidiendo con el selector.

---

## 4. Sin sobre-alcance

- `grep module_content_type` en `apps/`: solo 3 viewsets (convenios/internados/actividades).
- `calendar-activities`, `content-types`, auth y catálogos **no** están gateados por `IsModuleEnabled`.

---

## 5. Arquitectura / idioma

- Clase en inglés (`CalendarActivity`); tabla y columnas en español; `help_text`/`verbose_name` en español; docstrings en español.
- Vistas delgadas: escritura delega en `services.crear_actividad_calendario`/`actualizar_actividad_calendario` dentro de `transaction.atomic`; lógica temporal exclusivamente en `selectors.py`.
- Auditoría sin doble entrada: `perform_create`/`perform_update` del viewset **reemplazan** a los de `AuditedModelViewSet` y delegan en el service (que llama `registrar_auditoria` una vez). `DELETE` usa el `perform_destroy` heredado (una sola auditoría). Confirmado que no hay doble registro.
- Import lazy del selector dentro de `IsModuleEnabled.has_permission` (no a nivel de módulo): sin ciclo `common ↔ calendario`.

---

## 6. Observaciones informativas (no bloqueantes, sin acción requerida)

1. **`/auth/me/` usa 3 consultas para los módulos, no 2.** El spec T8 documenta "Total 2 queries", pero `_estado_modulos` ejecuta `content_types_controlados` + `content_types_habilitados` + resolución de metadatos = 3 consultas (más 1 de `perfiles`, ajena a esta feature). No hay N+1 y el resultado se cachea en la instancia, por lo que el criterio de aceptación real ("≈2 queries, sin N+1") se cumple en espíritu. Si se desea el conteo exacto documentado, podría fusionarse `controlados`/`habilitados` en una sola query agregada. Severidad: baja (discrepancia de docstring vs. implementación, sin impacto funcional).
2. **`code="MODULO_FUERA_DE_VENTANA"` no viaja en el body JSON.** El proyecto no tiene un exception handler personalizado; DRF serializa `PermissionDenied` como `{"detail": "El módulo está fuera de su ventana de registro."}` y el `code` queda solo como metadato del `ErrorDetail` (no visible para el frontend en el JSON). Esto es **consistente** con el resto del proyecto (p. ej. `exigir_ambito` levanta `PermissionDenied` sin `code`), por lo que cumple "el mismo mecanismo del proyecto". El frontend debe distinguir por el mensaje/estado `403`. Severidad: informativa.

---

## 7. Pendientes no bloqueantes (fuera del alcance de esta revisión)

- **T13 — Documentación** (`docs/db_schema_modulo_04_calendario.md`, `db_schema_er_global.md`, `CLAUDE.md`, `alcance_mvp.md`, `api_accesos_frontend.md`): se validan aparte.
- **T15 — `/code-review`**: se ejecuta aparte.
