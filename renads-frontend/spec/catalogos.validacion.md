# Validación — Módulo Catálogos (`/catalogos`)

> Revisión del Validator contra `spec/catalogos.md` (APROBADO) y el contrato del backend
> (`docs/api-catalogos.md`, `docs/api-convenios.md`, `docs/api-auth.md`,
> `docs/frontend-conventions.md`). **§5 (R1–R5) es autoritativa.**
>
> **Veredicto: APROBADO — módulo cerrado.** Sin hallazgos altos/medios. 24/24 tareas cumplidas.
> Sanidad técnica: `npx tsc --noEmit` OK, `npm run build` OK, `npm run lint` solo con los **2
> hallazgos PRE-EXISTENTES** ajenos al módulo.

## Sanidad técnica

- `npx tsc --noEmit`: **OK** (sin errores).
- `npm run build`: **OK** (compila; rutas `/catalogos`, `/catalogos/auditoria`,
  `/catalogos/documentos`, `/catalogos/representantes`, `/catalogos/entidades/[entidad]`,
  `/catalogos/listas/[catalogo]` presentes).
- `npm run lint`: 1 error + 1 warning, **ambos PRE-EXISTENTES y fuera del módulo**:
  - `components/layout/theme-toggle.tsx:18` — `react-hooks/set-state-in-effect` (conocido).
  - `components/ui/data-table.tsx:43` — `react-hooks/incompatible-library` (conocido, TanStack Table).
  - **Ningún hallazgo de lint nuevo introducido por el módulo Catálogos.**

## Estado por tarea

| Tarea | Estado | Nota |
|------|--------|------|
| T1 Tipos TS | OK | `Documento`/`AuditLog`/`Representante` con campos read-only exactos del contrato; entidades/catálogos vía `WithId` (patrón declarativo existente). Claves API sin traducir. |
| T2 Filtros declarativos | OK | `FilterConfig` en `lib/crud/types.ts`; `ResourceFilters` + `useList({filters})`; resetea `page`; limpia filtros. |
| T3 `readOnly` explícito | OK | Flag en `ResourceConfig`; `canWrite=!readOnly && userHasRole(...)`; Badge «Solo lectura». |
| T4 Hooks TanStack Query | OK | `createResourceHooks` reusado; `documents`/`audit-logs` con hooks propios; invalidación por `resourceKeys.all`. |
| T5 Centralizar entidades | OK | Origen único `lib/convenios/entities.ts` (`ENTITY_CONFIGS`); `/convenios/maestros` y `/catalogos` lo consumen; sin duplicación. |
| T6 Filtros 7 entidades | OK | `filterset_fields` exactos por entidad; `activo` boolean; FK con `EntityCombobox`. |
| T7 `university-authorities` | OK | Endpoint/filtros/search y campos R1 exactos (incl. `fecha_inicio_cargo`*, `referencia_documento_resolucion`). |
| T8 `faculties` / `professional-careers` | OK | Filtros y campos R1 exactos; `especialidad` opcional; FK a catálogos correctos. |
| T9 `university-campuses` | OK | Filtros `universidad`/`region`/`activo`; campos R1 exactos (`region`/`ubigeo` opcionales). |
| T10 `representatives` (v1) | OK | `disableCreate:true` (ALTA diferida); edición solo campos NO polimórficos (`nombre`,`cargo_ejecutivo`,`origen`,`fecha_inicio`,`fecha_fin`,`activo`); `tipo_contenido`/`id_objeto` solo lectura vía `renderEditInfo`; `// TODO(v2 content-types)` presente; filtros `tipo_contenido`/`id_objeto`/`cargo_ejecutivo`/`activo`. |
| T11 18 catálogos readOnly | OK | Los 18 slugs registrados con `readOnly:true`, columnas `codigo`/`nombre`/`activo`, filtro `activo`. |
| T12 `ubigeos` readOnly | OK | Filtros `departamento`/`provincia`/`distrito`/`activo`; columnas geográficas; paginación backend. |
| T13 API+hooks `documents` | OK | `lib/api/documents.ts` (Axios); POST `DocumentoWrite` solo 5 campos de escritura (nunca read-only); `url-descarga` como mutation; remove invalida lista; `// TODO(v2 content-types)`. |
| T14 Pantalla documentos (v1) | OK | List + filtros (`tipo_documento`,`estado`,`tipo_contenido`,`id_objeto`) + descargar (`window.open`) + eliminar; **sin ALTA** (R2); accesible a autenticado. |
| T15 API+hook `audit-logs` | OK | Solo lectura; filtros R3 (`usuario`,`accion_contiene`,`tipo_contenido`,`id_objeto`,`creado_en_desde`,`creado_en_hasta`); sin mutaciones. |
| T16 Pantalla auditoría | OK | Columnas del contrato; filtros R3 con date pickers; gating `Administrador RENADS`/`Auditor` con placeholder si no; orden `creado_en` desc (default backend). |
| T17 Índice `/catalogos` | OK | Tarjetas shadcn por sección; «Auditoría» solo Admin/Auditor. |
| T18 Ruta entidades | OK | Resuelve config por slug; estado «no encontrada» + volver. |
| T19 Ruta listas | OK | Contra `CATALOG_CONFIGS` (incluye `ubigeos`), `readOnly`. |
| T20 Rutas dedicadas | OK | `/representantes`, `/documentos`, `/auditoria` existen y montan su componente. |
| T21 Navegación | OK | `app-shell.tsx:46` ítem `/catalogos` con `["Administrador RENADS","Auditor"]` (R4). |
| T22 Estados carga/error/vacío | OK | Reutiliza `DataTable`/`DataTablePagination`; error con reintento; toasts `extractApiError`; mensajes de vacío. |
| T23 Idioma/convenciones | OK | UI español, claves API sin traducir; Axios solo en `lib/api/`; server-state solo TanStack Query; tablas vía `<DataTable>`; lint/build pasan. |
| T24 Gating UX | OK | Entidades/representantes escritura solo Admin (default `WRITE_ROLES`); documentos autenticado; auditoría Admin/Auditor; catálogos solo lectura. |

## Conformidad de contrato (§5)

- **R1 (campos exactos):** verificado entidad por entidad; todos los `fields` coinciden con R1
  (requeridos `*`, FK→endpoint correcto, `date`/`email`/`boolean`, `referencia_*` como texto).
- **R2 (polimorfismo / ALTA diferida):** confirmado. Representantes y documentos **sin create activo**
  en UI; `// TODO(v2 content-types)` en `lib/catalogos/representatives.tsx:43`,
  `lib/api/documents.ts:49`. El método `documentsApi.create` queda como andamiaje v2 (no cableado a UI)
  y nunca envía campos read-only.
- **R3 (audit-logs):** filtros y orden `creado_en` desc correctos.
- **R4 (menú):** ítem nav y gating por sección del índice correctos.
- **R5 (rutas):** segmentos `entidades`/`listas` correctos; sin `/catalogos/catalogos`; sin colisión
  con `/convenios/maestros`.

## Observaciones menores (BAJAS — no bloquean el cierre)

1. `app/(app)/catalogos/documentos/page.tsx` — la columna `cargado_por` (sugerida en T14) no se
   muestra; sí se incluyen tipo/archivo/destino/versión/estado/cargado_en. Sugerencia: añadir columna
   `cargado_por` si se desea trazabilidad de carga. (Cosmético.)
2. `lib/catalogos/entities.ts` (`university-authorities`) — la columna «universidad (etiqueta)»
   sugerida en T7 no se renderiza (requiere `universidad_nombre`/label del backend). Columnas son
   «sugeridas», no obligatorias. (Cosmético.)
3. `lib/api/audit-logs.ts` / pantalla auditoría — el filtro exacto `accion` (igualdad) no se expone en
   UI; se usa `accion_contiene` (icontains), más útil. Sin impacto funcional. (Informativo.)
4. La bitácora no envía `ordering` explícito; depende del default backend (`creado_en` desc), que el
   contrato garantiza. Aceptable; podría enviarse explícito para robustez. (Informativo.)
