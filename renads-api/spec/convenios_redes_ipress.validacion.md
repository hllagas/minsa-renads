# Validación — Refactor de BD del Módulo 1 (Convenios): Red/Microred, catálogos de clasificación y refactor de `ipress`

**Resultado: APROBADO (sin errores altos/medios).** Se genera la guía de pruebas manuales en `spec/convenios_redes_ipress.guia_pruebas.md`.

Fecha: 2026-08-13 · Rama: `feat/almacenamiento-adjuntos` · Migración: `0014_category_classificationtype_microred_and_more` (aplicada).

## Comprobaciones técnicas ejecutadas

| Comando | Resultado |
|---------|-----------|
| `manage.py check` | System check identified no issues (0 silenced). |
| `manage.py makemigrations --check --dry-run` | No changes detected (schema en sync). |
| `manage.py showmigrations convenios` | `[X] 0014_...` aplicada. |
| Resolución del router | `networks`, `micro-networks`, `categories`, `classification-types` con list+detail (CRUD), sin colisión de basename. |

## Cobertura del spec (T1–T18)

| Tarea | Estado | Notas |
|-------|--------|-------|
| T1 `Red` (tabla `red`) | OK | No hereda de `Catalog`; `unique_together=(ambito_geografico_sanitario, codigo)`; FK PROTECT + `db_column`; `related_name="redes"`; `ordering`; `__str__`. |
| T2 `Microred` (tabla `microred`) | OK | `unique_together=(red, codigo)`; FK PROTECT `red_id`; `related_name="microredes"`; definido después de `Red`. |
| T3 `Category` (tabla `categoria`) | OK | Hereda de `Catalog`, sin campos propios; `verbose_name`/plural en español. |
| T4 `ClassificationType` (tabla `tipo_clasificacion`) | OK | Hereda de `Catalog`, sin campos propios. |
| T5 Refactor `Ipress` | OK | 3 FK opcionales (PROTECT, `null/blank`, `db_column`); `related_name` sin colisión (`ipress_por_categoria/_clasificacion/_microred`); `latitud`/`longitud` Decimal(9,6); `cantidad_camas` PositiveInteger; `numero_ruc` CharField(11) blank. Campos previos conservados. |
| T6 Migración | OK | Una sola migración; crea 4 tablas y 7 columnas nuevas en `ipress`; todas nullable/blank (corre limpio sobre filas existentes); `unique_together` incluido; `--check` limpio. |
| T7 ViewSets CRUD (4 catálogos) | OK | En `ENTITY_VIEWSETS` con `_entity_viewset`; `filterset_fields`/`search_fields` según spec; permisos por defecto `[IsAuthenticated, IsAdminRoleOrReadOnly]`; heredan `AuditedModelViewSet`. No en `CATALOG_VIEWSETS`. |
| T8 CRUD `ipress` ampliado | OK | `IpressViewSet.filterset_fields` incluye `categoria`, `tipo_clasificacion`, `microred`; `_auto_serializer(fields="__all__")` expone/acepta los campos nuevos. |
| T9 Selectors | OK (N/A) | No hay selector de `ipress` con `select_related` que tocar; catálogos usan `_default_manager.all()`. Sin lógica de alcance nueva. |
| T10 Router | OK | Registro automático vía bucle `ENTITY_VIEWSETS`; rutas `networks`, `micro-networks`, `categories`, `classification-types` disponibles bajo `/api/v1/`. |
| T11 Filtros | OK | Cubiertos por `filterset_fields`. |
| T12 Permisos | OK | Reutiliza `IsAdminRoleOrReadOnly`; catálogos globales sin scope institucional. |
| T13 Admin | OK | `apps/convenios/admin.py` creado; registra los 4 modelos con `list_display`/`list_filter`/`search_fields` según criterios. No rompe registros previos (no existía admin.py). |
| T14 Validación RUC | OK | `RegexValidator(r"^\d{11}$")` a nivel de campo del modelo (se propaga al `_auto_serializer`); `blank=True` permite vacío. Decisión documentada en help_text/modelo. |
| T15 `db_schema_modulo_01_convenios.md` | OK | §2 catálogos (`categoria`, `tipo_clasificacion`), §2 nueva jerarquía `red`/`microred` con `unique_together`, §3 `ipress` con las 7 columnas nuevas, §12 mapa de relaciones. Coincide campo a campo con los modelos. |
| T16 `db_schema_er_global.md` | OK | Mermaid §1 incluye `ambito_geografico_sanitario ||--o{ red`, `red ||--o{ microred`, `microred ||--o{ ipress`, `categoria/tipo_clasificacion ||--o{ ipress`; se conservan relaciones previas. |
| T17 Tests | PENDIENTE (no bloqueante) | Fuera de alcance de testing automatizado del MVP; el spec lo condiciona a exigencia del orquestador. Ver casos manuales en la guía de pruebas. |
| T18 `/code-review` y `/fix-types` | PENDIENTE (no bloqueante) | Skills no disponibles en el subagente; ejecutar en cierre. `manage.py check` y `makemigrations --check` limpios. |

## Verificación contra schema

- Tablas `red`, `microred`, `categoria`, `tipo_clasificacion` y columnas nuevas de `ipress` (`categoria_id`, `tipo_clasificacion_id`, `microred_id`, `latitud`, `longitud`, `cantidad_camas`, `numero_ruc`) coinciden con los modelos en tipo, nullability y `unique_together`.
- Descripciones de columnas en español; nombres de tabla/columna en español; clases en inglés.

## Verificación contra arquitectura

- `on_delete=PROTECT` en todas las FK nuevas; `db_column` en español consistente.
- Naming: clase inglés / tabla-columna-help_text español / `related_name` explícito y sin colisión.
- CRUD vía `ENTITY_VIEWSETS` con `IsAdminRoleOrReadOnly` + auditoría (`AuditedModelViewSet`).
- Router bajo `/api/v1/` (montado por `config/urls` sobre el router de `apps/convenios/urls.py`).

## Pendientes registrados (no bloqueantes)

1. T17 — pruebas automatizadas de CRUD, `unique_together`, RUC inválido y `PROTECT` (409).
2. T18 — ejecutar `/code-review` y `/fix-types` en el cierre de la implementación.
