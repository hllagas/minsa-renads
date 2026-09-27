# Validación 2 — Rediseño Coordinator.universidad

**Fecha:** 2026-09-26
**Rama:** main
**Resultado:** APROBADO — sin errores altos ni medios

---

## Checklist de puntos críticos

| # | Punto | Estado | Detalle |
|---|-------|--------|---------|
| 1 | `Coordinator.universidad` FK NOT NULL | OK | `ForeignKey(University, PROTECT, db_column="universidad_id", related_name="coordinadores")`, sin `null=True`, posición correcta (después de `tutor`, antes de `tipo_documento_identidad`) |
| 2 | `CoordinatorSede` sin `universidad`, nuevo `unique_together` | OK | `unique_together = [("coordinador", "ipress")]`; `__str__` usa solo `coordinador_id` e `ipress_id` |
| 3 | `CoordinatorSerializer.universidad` write obligatorio + `universidad_detalle` read-only | OK | `PrimaryKeyRelatedField(queryset=...)` en `Meta.fields`; `SerializerMethodField` exposición en lectura |
| 4 | N+1 en `CoordinatorSedeSerializer.universidad_detalle` | OK | Vistas `sedes` (GET) y `sede_detail` hacen `select_related("coordinador__universidad", "ipress")` |
| 5 | `crear_coordinador_sede` sin param `universidad` | OK | Firma `(*, coordinador, ipress, usuario)`; `universidad = coordinador.universidad` derivado internamente; `create(coordinador=coordinador, ipress=ipress)` |
| 6 | `asignar_tutor_coordinador_sede` filtro RN-CRD-06 | OK | Usa `coordinador_sede__coordinador__universidad=coordinador_sede.coordinador.universidad` |
| 7 | `listar_sedes_disponibles` ORM correcto | OK | Path `unidad_ejecutora__convenios__tipo_convenio__codigo` verificado contra `related_name="convenios"` en `ExecutingUnit`; `distinct()` presente |
| 8 | `filterset_fields` usa `"universidad"` directo | OK | `filterset_fields = ["activo", "universidad", "sedes__ipress"]` — campo directo en el modelo |
| 9 | Migraciones en orden correcto y `--check` limpio | OK | `0033`: AddField nullable + RunPython backfill (`atomic=False`); `0034`: AlterField NOT NULL + AlterUniqueTogether + RemoveField en orden correcto. `manage.py check` = 0 issues; `makemigrations --check` = No changes detected |
| 10 | Docs `db_schema_modulo_02_internados.md` §5 | OK | `universidad_id` en tabla `coordinador` (NOT NULL); ausencia de `universidad_id` en `coordinador_sede`; mapa §9 actualizado |

---

## Sanidad técnica

- `python manage.py check --settings=config.settings.docker` → **0 issues**
- `python manage.py makemigrations --check --dry-run --settings=config.settings.docker` → **No changes detected**

---

## Observaciones (informativas, sin bloqueo)

### OBS-1 — Alcance de exclusión en `listar_sedes_disponibles` (baja prioridad)

`apps/internados/services.py:180`

El plan original planteaba excluir sedes asignadas a **cualquier** coordinador de la misma universidad (`CoordinatorSede.objects.filter(coordinador__universidad=universidad)`). La implementación excluye solo las sedes asignadas al **coordinador en cuestión** (`CoordinatorSede.objects.filter(coordinador=coordinador)`). El schema no impone unicidad `(universidad, sede)` en `coordinador_sede`, solo `(coordinador, sede)`, por lo que la implementación es conforme al schema. Si el requisito de negocio es que una sede no pueda tener dos coordinadores de la misma universidad, se debe revisar con el product owner y ajustar la exclusión y/o añadir un constraint.

### OBS-2 — `get_universidad_detalle` con guard `if u is None` redundante (cosmético)

`apps/internados/serializers.py:267`

`universidad` es NOT NULL en el modelo, así que el check `if u is None` es defensa extra benigna. No afecta comportamiento.
