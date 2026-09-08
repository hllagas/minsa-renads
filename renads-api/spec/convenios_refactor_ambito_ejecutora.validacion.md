# Validación — Refactor Ámbito Geográfico Sanitario + Unidad Ejecutora

**Módulo:** `apps/convenios`
**Fecha:** 2026-09-08
**Resultado:** EXITOSA — sin errores altos ni medios.

---

## Resultado global

`python manage.py check` → `System check identified no issues (0 silenced).`
`python manage.py makemigrations --check --dry-run` → `No changes detected`

---

## Verificación por tarea

| Tarea | Archivo verificado | Resultado |
|-------|--------------------|-----------|
| T-01 — FK `gobierno_regional` en `HealthGeographicScope` | `models.py:42-53` | OK |
| T-02 — Migración 0043: AddField + RunPython backfill | `migrations/0043_healthgeographicscope_gobierno_regional.py` | OK |
| T-03 — Vista `health-geographic-scopes` con `detalles` | `views.py:825-830` | OK |
| T-04 — Schema docs: tabla `ambito_geografico_sanitario` | `docs/db_schema_modulo_01_convenios.md:79-91` | OK |
| T-05 — Análisis de datos previo (comentario en migración 0044) | `migrations/0044_..._transitorio.py:1-23` | OK |
| T-06 — Migración 0044: columnas transitorias + backfill | `migrations/0044_..._transitorio.py` | OK |
| T-07 — Modelo `ExecutingUnit` rediseñado; FKs `Ipress` y `Convention` con `to_field="codigo"` | `models.py:360-381, 385-389, 860-865` | OK |
| T-08 — Migración 0045: pasos A→B→C→D completos | `migrations/0045_executingunit_nueva_estructura.py` | OK |
| T-09 — Vista `executing-units`: sin logo, filtros y detalles actualizados | `views.py:860-866` | OK |
| T-10 — `pdf.py _domicilio_entidad` rama UNIDAD_EJECUTORA devuelve `""` | `pdf.py:71-72` | OK |
| T-11 — `serializers.py get_unidad_ejecutora_detalle` compatible | `serializers.py:75-76` | OK |
| T-12 — `services.py` sin referencias a campos eliminados | `services.py` (búsqueda exhaustiva) | OK |
| T-13 — Filtros: sin cambios requeridos en `ConventionFilter` ni `IpressViewSet` | `filters.py` | OK |
| T-14 — Schema docs: tabla `unidad_ejecutora` y sección 12 actualizadas | `docs/db_schema_modulo_01_convenios.md:172-187, 695-706` | OK |

---

## Observaciones

- El campo `gobierno_regional` en `_detalle_nombre` devuelve `{"id": <int>, "codigo": null, "nombre": "..."}` (el modelo `RegionalGovernment` no tiene campo `codigo`; `getattr(rel, "codigo", None)` retorna `None`). Esto es coherente con lo descrito en el spec T-03 y no constituye un error.
- La migración 0044 documenta correctamente que la tabla `unidad_ejecutora` tiene 0 filas en desarrollo, por lo que el backfill de datos es un noop. Los RunPython incluyen la lógica de colisión/integridad para entornos con datos reales.
- La migración 0045 incluye un Paso D adicional (AlterField finales D1-D5) para llevar los campos al estado exacto del modelo Python (db_column canónico, related_name, verbose_name). Este paso es correcto y resuelve el posible desacuerdo entre el estado de migración y el modelo que `makemigrations --check` detectaría.
