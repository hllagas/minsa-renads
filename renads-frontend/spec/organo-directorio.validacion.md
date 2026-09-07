# Validación — «OrganDirectory: FK `organo` + unicidad (organo, gobierno_regional, nombre)»

> Fecha: 2026-09-07 · Estado: **IMPLEMENTADO y verificado** (backend end-to-end + front tsc/lint).
> Spec aprobado: decisiones P1=`Organ.nombre`, P2=`organo__nombre`, P3=renombrar clave a `organo`,
> P4=inyección en pantalla, P5=fallar ante colisiones.

## Backend

| Tarea | Resultado |
|-------|-----------|
| B1 | `OrganDirectory.categoria` (CharField) → FK `organo`→Organ (PROTECT, NOT NULL); 2 constraints parciales (`uniq_organo_dir_organo_gore_nombre`, `uniq_organo_dir_organo_nombre_sin_gore`); quita `uniq_organo_directorio_por_gore`. ✅ |
| B2 | Migración `0039_organdirectory_organo_fk`: add nullable → data migration (map por `Organ.nombre`) + verificación de colisiones (0) → NOT NULL → drop `categoria` → swap constraints. `0040` = AlterField no-op de `limit_choices_to`. `migrate` limpio; **15 filas** mapeadas (ORGANO_MINSA→"MINSA Administrativo", etc.), 0 sin organo, 0 colisiones. `reverse_code` repuebla `categoria`. ✅ |
| B3 | `_OrganDirectorySerializer`: `organo_detalle` + validación nueva (con/sin GORE, comparación exacta) → 400 en `nombre`. ✅ |
| B4 | `University.tipo_entidad`/`ExecutingUnit.tipo_organo` `limit_choices_to={"organo__nombre": ...}`. ✅ |
| B5 | `pdf._seleccionar_plantilla` remapeado a `Organ.nombre` (`"MINSA DIRIS"`, `"Gobierno Regional"`). ✅ |
| B6 | `_detalle_organo_directorio` clave `categoria`→`organo`; viewset filterset `organo`; `select_related("gobierno_regional","organo")`; comentarios actualizados. ✅ |
| B7 | `docs/api-catalogos.md` §2 (filtro `organo`, RN nueva, campo `organo` FK). ✅ |

### Smoke backend (shell, sobre BD real)
1. Duplicar `(organo, gore, nombre)` exacto → **400** «…mismo órgano y gobierno regional». ✅
2. Mismo GORE, nombre distinto → **válido**. ✅
3. Duplicar `(organo, nombre)` con GORE nulo (MINSA) → **400** «…mismo órgano». ✅
4. `pdf._seleccionar_plantilla`: MARCO/`Gobierno Regional`→`modelo_2_marco_region.docx`; ESPECIFICO/`MINSA DIRIS`→`modelo_3_especifico_lima.docx`. ✅
5. `manage.py check` sin issues; `makemigrations --check` sin cambios pendientes. ✅

## Frontend

| Tarea | Resultado |
|-------|-----------|
| T1 | `gen:api` → `schema.d.ts` con `organo`/`organo_detalle`, filtro `?organo`, sin `CategoriaEnum` de OrganDirectory. ✅ |
| T2 | `lib/catalogos/organs.ts`: `useOrgans`, `organIdByNombre`, `ORGAN_NOMBRE`. ✅ |
| T3 | `entities.ts` organ-directories: columna/filtro/campo `categoria`→`organo` (select contra `organs`, muestra `organo_detalle.nombre`). Eliminados `ORGAN_DIRECTORY_CATEGORY`/`categoriaLabel`. ✅ |
| T4 | University.tipo_entidad / ExecutingUnit.tipo_organo: sin `optionsParams:{categoria}`; la página `[entidad]` inyecta `optionsParams:{organo:<id resuelto>}` vía `useOrgans` (id puro, B2). ✅ |
| T5 | `representantes-entities.ts`: `params:{categoria}` → marker `organoNombre`; la pantalla resuelve el id y filtra `?organo=<id>` en el paso 2. ✅ |
| T6 | Único consumidor de `organo_directivo_detalle` (`catalogs.ts`) lee `.nombre`, no `.categoria` → sin cambios. ✅ |
| T7 | `CLAUDE.md` (fila refactor + bullets; marca el 2026-08-30 como SUPERSEDED). ✅ |
| T8 | `npx tsc --noEmit` limpio; `npm run lint` sin errores nuevos (2 restantes pre-existentes en `university-careers/page.tsx`). ✅ |

## Pendiente (no bloqueante)
- **Smoke manual UI con login** (Administrador RENADS): alta/edición de organ-directory eligiendo `organo`; crear un GORE con 2 órganos de nombre distinto (permite) y duplicar exacto (400); selects de University/UE (`?organo=<id>` en Network); representantes MINSA/GORE/DIRIS; generar PDF Marco/GORE y Específico/DIRIS. Los flujos equivalentes ya se validaron en shell.
