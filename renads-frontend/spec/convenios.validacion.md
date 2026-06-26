# Validación — Módulo `convenios`

## Pase 2 (Bloque 3 — flujo): ✅ APROBADO. **MÓDULO CERRADO.**

Revisado contra `spec/convenios.md` (T3.1–T3.3, T4.2) y contrato `docs/api-convenios.md`.

### Cobertura
| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| T3.1 API+hooks acciones | ✅ | `lib/convenios/flow.ts` (`useFlowAction` + `useCamposClinicos`/`useParticipantes`/`useHistorial`) |
| T3.2 UI acciones gateadas | ✅ | `flow-action-dialog.tsx` + 8 acciones en `flow-actions.ts`; detalle filtra por `userHasRole` + `onlyEspecifico` |
| T3.3 Pestañas | ✅ | Detalle con Tabs Datos/Campos clínicos/Participantes/Historial (`SimpleObjectTable`) |
| T4.2 Guía pruebas | ✅ | `spec/convenios.guia_pruebas.md` generada |

### Conformidad (Pase 2)
- **Contrato (backend real, convenio id=4):** GET `historial`/`participantes`/`campos-clinicos` → arrays (1 participante, 1 campo). POST `cambiar-estado` con estado inválido → `400` (manejado vía toast). ✓
- **Roles:** cada acción visible solo para su grupo (DIGEP/CONAPRES/OGAJ/SG/Admin); CONAPRES y campos clínicos además solo en Específico. ✓
- **Stack:** acciones vía `useFlowAction` (mutation Query); listas vía queries; invalidación de detalle + flujo al mutar. ✓

### Hallazgos (Pase 2)
- ~~`entity-combobox.tsx` llama `api.get` directamente~~ → **RESUELTO.** Extraído a
  `lib/api/lookup.ts` (`searchResource`, `getResourceItem`). Verificado: 0 `axios`/`fetch` en
  `app/`/`components/`.
- **`esEspecifico`** se infiere del nombre del tipo (`/espec/i`) porque el read da el nombre, no el
  código. Soft-gating; el backend es la autoridad (rechaza CONAPRES/campos en Marco). Aceptable.
- **`firma`/`participantes`**: `*_tipo_contenido` como número (misma deuda del solicitante; sin
  endpoint de ContentTypes). Documentado.
- **Enums de acciones**: solo evaluación usa choices (`VALIDADO`/`OBSERVADO`); el resto texto libre
  (OpenAPI no expone esos enums). El backend valida.

### Comprobaciones técnicas (Pase 2)
- `npm run lint` → 0 errores; `npm run build` → 9 rutas OK.

---

## Pase 1 (Bloques 0–2): ✅ APROBADO (sin errores altos/medios)

Revisado contra `spec/convenios.md`, contrato `docs/api-convenios.md` y convenciones del proyecto.
**Bloque 3 (flujo) pendiente — Pase 2.** El módulo no se cierra hasta completar Pase 2.

### Cobertura del spec (Pase 1)
| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| T0.1 Tipos OpenAPI | ✅ | `lib/api/schema.d.ts` generado; script `gen:api` en package.json |
| T0.2 Helpers query | ✅ | `lib/api/query.ts` (`createResourceApi`, `buildListParams`, `resourceKeys`), `lib/crud/hooks.ts` (`createResourceHooks`) |
| T0.3 Componentes apoyo | ✅ | `PageHeader`, `DataTablePagination`, `EntityCombobox` (búsqueda server-side) |
| T1.1 Hooks catálogos | ✅ | Selects vía `EntityCombobox` consultando `/{endpoint}/?search=` (sin hooks de lista estáticos) |
| T1.2 API+hooks entidades | ✅ | CRUD genérico aplica a las 7 entidades vía `createResourceHooks` |
| T1.3 UI maestros | ✅ | `/convenios/maestros` + `/convenios/maestros/[entidad]` (7 entidades); escritura gateada a `Administrador RENADS` |
| T2.1 API layer convenios | ✅ | `conventionHooks` (`conventions`, read/write tipados) |
| T2.2 Hooks convenios | ✅ | list/detail/create/update/remove con invalidación |
| T2.3 Lista | ✅ | `/convenios` DataTable + filtros `tipo_convenio`/`estado_actual` + búsqueda + paginación server-side |
| T2.4 Alta/edición | ✅ | `/convenios/nuevo`, `/convenios/[id]/editar` (rhf, ResourceForm) |
| T2.5 Detalle | ✅ | `/convenios/[id]` con `estado_actual`/`estado_codigo` |
| T4.1 lint/build | ✅ | `npm run lint` 0 errores; `npm run build` 9 rutas OK |

### Conformidad
- **Stack:** toda petición vía TanStack Query; **0** `fetch`/`axios` en `app/`/`components/`; Axios solo en capa `lib/` (`query.ts`, `options.ts`, `auth.ts`). Tablas vía `<DataTable>` (TanStack Table). ✓
- **Contrato (backend real):** listas devuelven forma paginada DRF (`count/next/previous/results`) en las 10 endpoints probadas. CRUD roundtrip **POST→PATCH→DELETE** en `conapres` con el payload del front → OK. ✓
- **Next/SOLID:** CRUD declarativo config-driven (1 componente + 7 configs); capas separadas (api/hooks/UI); `"use client"` solo donde corresponde. ✓
- **Gating:** escritura de maestros y acciones gateadas a `Administrador RENADS` (`userHasRole`); el backend es la autoridad final. ✓

### Hallazgos / limitaciones (aceptados para MVP, no bloquean Pase 1)
- **`solicitante` polimórfico** (`/convenios/nuevo`): se capturan `solicitante_tipo_contenido` y
  `solicitante_id_objeto` como números. No hay endpoint de ContentTypes en el contrato → un selector
  entidad/tipo queda **pendiente**. El backend valida; create funciona con ids correctos.
- **Editar convenio** excluye `tipo_convenio` (el read serializer devuelve el nombre, no el id →
  no pre-rellenable). PATCH parcial. Correcto para MVP; documentado.
- ~~`CatalogSelect` muestra solo la 1ª página (PAGE_SIZE 20)~~ → **RESUELTO.** Reemplazado por
  `EntityCombobox` con **búsqueda server-side** (`/{endpoint}/?search=`), que escala a catálogos
  grandes (ubigeo, convention-statuses 26). Resuelve la etiqueta del valor seleccionado al editar
  (consulta el detalle por id). Verificado contra backend (`?search=vigente` → "Vigente").
- **RN-3 (Específico→Marco vigente)** no se valida en el cliente (no se detecta el tipo "Específico"
  sin inspeccionar el catálogo); se delega al backend y se muestra su error. Aceptable.

### Comprobaciones técnicas
- `npm run lint` → 0 errores, 1 warning (DataTable/React Compiler, ajeno).
- `npm run build` → OK (`/convenios`, `/convenios/[id]`, `/[id]/editar`, `/maestros`, `/maestros/[entidad]`, `/nuevo`).
- Smoke API (superusuario): 10 listas con forma paginada; CRUD roundtrip en `conapres` OK.

### Pendiente para cerrar el módulo
- **Pase 2 — Bloque 3 (flujo):** acciones por rol (cambiar-estado, evaluación técnica, opiniones,
  campos clínicos, firma, publicación, participantes, historial) + pestañas en el detalle.
- **T4.2:** guía de pruebas manuales (`spec/convenios.guia_pruebas.md`) al cerrar el módulo.
- Deuda `CatalogSelect`/combobox server-side → **saldada** (`EntityCombobox`). Queda pendiente el
  selector de solicitante (polimórfico, requiere endpoint de ContentTypes inexistente).
