# Validación — `convenios_tipo_entidad_universidad`

**Resultado:** EXITOSO — sin errores altos ni medios.

**Fecha:** 2026-09-18
**Commit base revisado:** rama `main`, archivos sin stagear (modificados: `models.py`, `views.py`, ambos docs; sin stagear: `migrations/0052_university_entity_type.py`, `spec/convenios_tipo_entidad_universidad.md`).

---

## Resumen de hallazgos por checklist

| # | Ítem del checklist | Estado | Detalle |
|---|-------------------|--------|---------|
| 1 | `UniversityEntityType` en `models.py`: `db_table`, campos, sin herencia de `Catalog`, `__str__` | OK | `models.py` L639-658; `db_table="tipo_entidad_universidad"`, `nombre` varchar 100 unique, `activo` bool default True, `__str__` devuelve `nombre`. |
| 2 | `University.tipo_entidad` apunta a `UniversityEntityType`, `on_delete=PROTECT`, `db_column="tipo_entidad_id"`, sin `limit_choices_to` | OK | `models.py` L669-673; FK a `UniversityEntityType`, PROTECT, `db_column="tipo_entidad_id"`, sin `limit_choices_to`. |
| 3 | Migración `0052`: 4 pasos en orden, depende de `0051` | OK | `migrations/0052_university_entity_type.py`; `dependencies=[("convenios","0051_...")]`; operaciones: `CreateModel` → `RunPython(seed_tipos)` → `RunPython(migrar_tipo_entidad)` → `AlterField`. |
| 4 | Seed: exactamente 4 filas en el orden correcto | OK | `seed_tipos` inserta `["Universidad","Instituto","Escuela superior","Escuela de posgrado"]` con `get_or_create` idempotente. |
| 5 | Backfill: matching por nombre, default `"Universidad"` + warning | OK | `migrar_tipo_entidad` resuelve por `OD.objects.filter(pk=univ.tipo_entidad_id)`, hace fallback a `default_tipo` y `print("[WARN]...")`. |
| 6 | `python manage.py makemigrations --check --dry-run` sin cambios | OK | Salida: `No changes detected`. |
| 7 | `python manage.py check` pasa | OK | Salida: `System check identified no issues (0 silenced)`. |
| 8 | `UniversityEntityTypeViewSet`: `ReadOnlyModelViewSet`, `IsAuthenticated`, `filterset_fields=["activo"]`, `search_fields=["nombre"]`, serializer `id/nombre/activo` | OK | `views.py` L874-883; hereda `ReadOnlyModelViewSet`, permiso `IsAuthenticated`, `_auto_serializer(m.UniversityEntityType)`. |
| 9 | `university-entity-types` en `CATALOG_VIEWSETS` | OK | `views.py` L897; entrada `"university-entity-types": UniversityEntityTypeViewSet`. |
| 10 | `POST /api/v1/university-entity-types/` devuelve 405 | OK (estructural) | `ReadOnlyModelViewSet` no define action `create`; DRF devuelve 405 automáticamente. |
| 11 | `GET /api/v1/universities/` con `tipo_entidad_detalle` sin error 500 | OK | `_detalle_nombre` en `views.py` L507 usa `getattr(rel, "codigo", None)` → devuelve `None` para `UniversityEntityType` (sin campo `codigo`). Sin error. |
| 12 | `ConventionReadSerializer.tipo_entidad_universidad` sin cambio funcional | OK | `serializers.py` L47-48; `source="universidad.tipo_entidad.nombre"` funciona porque `UniversityEntityType` también tiene `nombre`. |
| 13 | `selectors.py` `select_related("universidad__tipo_entidad")` sin modificar | OK | `selectors.py` L26; nombre del campo de acceso no cambia; sin modificación al selector. |
| 14 | `docs/db_schema_modulo_01_convenios.md` actualizado | OK | Tabla `tipo_entidad_universidad` en sección 2 (L48); sección nueva `tipo_entidad_universidad` con columnas y endpoint (L50-62); `universidad.tipo_entidad_id` actualizada a `FK → tipo_entidad_universidad` (L263); sección `tipo_organo RETIRADA` actualizada (L124); mapa de relaciones actualizado (L731). |
| 15 | `docs/api_almacenamiento_frontend.md` contiene sección `university-entity-types` | OK | L377-406; endpoint, respuesta JSON, uso como filtro y nota de breaking change de IDs. |
| 16 | `services.py` no modificado | OK | No aparece en `git status`; confirmado en historial: último toque en commit `2f80af8` (antes de esta implementación). |
| 17 | `apps/convenios/urls.py` no modificado directamente | OK | No aparece en `git status`; el router itera `CATALOG_VIEWSETS` automáticamente. |
| 18 | `migrate` y `test` no ejecutados por `implement` | OK | Solo `makemigrations` y `check` fueron invocados. |

---

## Observación menor (informativa, no bloquea)

**`migrar_tipo_entidad` no usa `select_related`:** la función itera `Universidad.objects.all()` sin `select_related("tipo_entidad")`. Dado que el campo `tipo_entidad_id` en esa etapa aún apunta a `organo_directorio`, acceder a `univ.tipo_entidad_id` (PK raw) es suficiente y no genera N+1 real; la consulta a `OD` es explícita por `pk`. Sin impacto funcional ni de correctitud; potencial degradación de rendimiento solo si hay miles de universidades (MVP no aplica). No requiere corrección.

---

La implementación cubre todos los ítems del checklist de la sección 6 del spec. Se procede a generar la guía de pruebas manuales.
