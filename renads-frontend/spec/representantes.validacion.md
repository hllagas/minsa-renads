# Validación — Feature «Representantes/Autoridades multi-entidad»

> Fecha: 2026-09-07 · Estado: **IMPLEMENTADO y verificado** (backend end-to-end + front tsc/lint).
> Spec: `spec/representantes.md` (aprobado). Decisiones §8: D2=eliminar limpio, D3-sub=NO,
> D5=endpoint nuevo, ConventionParty=fuera de alcance, B8=filtro añadido.

## Backend (`apps/convenios`)

| Tarea | Resultado |
|-------|-----------|
| B1/B3 | `OrganRepresentative` + `OrganRepresentativeHistory` ganan `tipo_contenido`+`id_objeto`+`entidad` (GenericFK); `organo_directorio` eliminado del modelo. Índice `idx_org_repr_entidad`. ✅ |
| B2 | Migración `0038_organrepresentative_polimorfico`: add nullables → data migration (pobló desde `organo_directorio`) → NOT NULL → RemoveField `organo_directorio`. `migrate` limpio; **2 filas migradas** a `organdirectory` con `id_objeto` correcto, 0 huérfanas. `reverse_code` repuebla. ✅ |
| B4 | `registrar_organo_representante` baja al anterior por par `(tipo_contenido, id_objeto, cargo_ejecutivo)`; snapshot copia campos genéricos. ✅ |
| B5 | Serializer: `entidad_detalle {tipo,id,nombre}`; valida unicidad de documento, ContentType permitido (5 modelos) y coherencia cargo↔entidad (D4). ✅ |
| B6 | ViewSet filtros `tipo_contenido`/`id_objeto`/`cargo_ejecutivo`/`activo`; `select_related` sin GFK; history igual. ✅ |
| B7 | `GET /representante-content-types/` → 5 ContentTypes (`conapres, executingunit, ipress, organdirectory, university`). ✅ |
| B8 | `executive-positions` filterset → `{"organo_directivo": ["exact","isnull"], "activo":["exact"]}`; `?organo_directivo__isnull=true` en schema. ✅ |
| B9 | `docs/api-catalogos.md` §3 reescrita (modelo polimórfico, endpoint, RN cargos). ✅ |
| — | Efecto colateral: `_validar_coherencia_parte` (ConventionParty) actualizado al modelo genérico (lee `entidad`, no la columna eliminada). Sin ampliar alcance. ✅ |

### Smoke backend (shell)
1. Universidad + **cargo global** → serializer válido. ✅
2. Cargo **por órgano** (OrganDirectory) aplicado a Universidad → 400 «El cargo no corresponde a la entidad seleccionada.» ✅
3. `registrar_organo_representante` crea; `entidad_detalle = {tipo: university, id, nombre}`. ✅
4. `manage.py check` sin issues; `makemigrations --check` sin cambios pendientes. ✅

## Frontend

| Tarea | Resultado |
|-------|-----------|
| T1 | `npm run gen:api` regeneró `schema.d.ts` (`entidad_detalle`, `representante-content-types`, `organo_directivo__isnull`). ✅ |
| T2 | `lib/catalogos/representantes-entities.ts`: 7 opciones UI, `resolveTipoContenidoId`, `listRepresentanteTypes`. ✅ |
| T3–T5 | `/catalogos/representantes` rediseñada a 2 pasos (tipo → entidad); diálogo polimórfico (payload `tipo_contenido`+`id_objeto`); cargos globales ∪ por órgano (fusión sin duplicar). ✅ |
| T6 | Errores del backend vía `extractApiError` (toast). ✅ |
| T7 | `lib/catalogos/representatives.tsx` (dead code) eliminado. ✅ |
| T9 | `CLAUDE.md` (fila refactor + bullet) y `docs/api-catalogos.md` actualizados. ✅ |
| T10 | `npx tsc --noEmit` limpio; `npm run lint` sin errores nuevos (los 2 errores restantes son pre-existentes en `university-careers/page.tsx`). ✅ |

## Pendiente (no bloqueante)
- **Smoke manual UI con login** (rol `Administrador RENADS`): registrar un representante por cada uno de los 7 tipos desde la pantalla y confirmar en Network `tipo_contenido`/`id_objeto`. El flujo equivalente ya se validó vía serializer/service en shell.
- **ConventionParty ampliado** a representantes de universidades/UE → ciclo SDD futuro (fuera de alcance).
