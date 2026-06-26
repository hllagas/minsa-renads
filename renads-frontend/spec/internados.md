# Spec — Módulo `internados` (Registrar Internados)

Módulo 3 del MVP (`docs/mvp.md`). CRUD + flujo de internos, tutores, internados y rotaciones.
Contrato del backend: **`docs/api-internados.md`**. Reutiliza toda la infraestructura del módulo
Convenios (CRUD genérico, `EntityCombobox`, `ResourceForm`, `SimpleObjectTable`, `useFlowAction`,
patrón de detalle con pestañas + acciones gateadas).

> **Estado:** ✅ **MÓDULO CERRADO.** Implementado en un pase, validado sin errores. Ver
> `spec/internados.validacion.md` y `spec/internados.guia_pruebas.md`.

## Resumen / pantallas
- **Internados** `/internados`: lista (DataTable + filtros + paginación), detalle con pestañas
  (Datos, Rotaciones, Historial) + acciones de flujo, alta/edición.
- **Rotaciones**: gestionadas desde el detalle del internado (lista + crear) y con acciones propias
  (autorizar, iniciar, cambiar-estado, historial).
- **Maestros del módulo**: `interns` y `tutors` (CRUD); catálogos como selects.

## Reglas de negocio relevantes (UX; el backend es autoridad)
- Internado solo sobre **Convenio Específico vigente** (`VIGENTE`/`PUBLICADO`/`SUSCRITO`); `tutor` obligatorio.
- Duración ≤ 1 año; rotación entre IPRESS del **mismo ámbito geográfico sanitario**; **máx. 4 rotaciones**.
- Autorizar rotación: solo **autoridad firmante** del Convenio Específico; no inicia sin autorización aprobada.

## Reutilización (ya existe — módulo Convenios)
- CRUD declarativo: `lib/crud/*`, `components/crud/*`, `ResourceCrud`, `ResourceForm`.
- `EntityCombobox` (búsqueda server-side), `lib/api/lookup.ts`, `lib/api/query.ts`.
- Flujo: `useFlowAction` (genérico; sirve para internados/rotaciones cambiando el recurso base),
  `FlowActionDialog`, `SimpleObjectTable`, patrón de detalle con `Tabs`.
- Tipos: regenerar/usar `lib/api/schema.d.ts` (`InternshipRead/Write`, `RotationRead/Write`, `Intern`, `Tutor`, ...).

---

## Bloque 0 — Infra del módulo
- [x] **T0.1** Regenerar tipos (`npm run gen:api`) y exponer alias de internados desde `schema.d.ts`.
- [x] **T0.2** Generalizar `useFlowAction` para aceptar el recurso base (hoy fijo a `conventions`):
  parametrizar a `internships`/`rotations`. Criterio: reutilizable sin duplicar lógica.

## Bloque 1 — Personas (CRUD maestros)
- [x] **T1.1** Config + UI CRUD de **`interns`** (filtros: universidad, carrera, especialidad,
  documento; búsqueda por documento/nombres). FKs vía `EntityCombobox` (universities,
  professional-careers, specialties, identity-document-types). Escritura rol `Universidad`/`Administrador RENADS`.
- [x] **T1.2** Config + UI CRUD de **`tutors`** (filtros: especialidad, ipress, documento). FKs:
  specialties, ipress, identity-document-types.
- [x] **T1.3** Catálogos como selects: `internship-statuses`, `rotation-statuses`, `service-areas`,
  `identity-document-types` (vía `EntityCombobox`, sin CRUD propio).
  - **Criterio:** CRUD de interns/tutors funciona contra el backend con alcance/rol correctos.

## Bloque 2 — Internados (núcleo CRUD + flujo)
- [x] **T2.1 API/hooks** `internships` (read/write tipados) con `createResourceHooks`.
- [x] **T2.2 Lista** `/internados`: `<DataTable>` con columnas (interno, convenio, ipress, tutor,
  estado, fechas), filtros backend (`convenio`, `ipress`, `tutor`, `estado_actual`,
  `ambito_geografico_sanitario`, rangos de fecha), búsqueda por interno, paginación. "Nuevo" gateado a `Universidad`.
- [x] **T2.3 Alta/edición**: form rhf (`ResourceForm`) con campos de escritura (interno, convenio,
  campo_clinico, ipress, tutor, ambito_geografico_sanitario, fechas, observaciones). Edición usa el
  subconjunto editable (`ipress`, `observaciones`, `fecha_inicio`, `fecha_fin`); el tutor se cambia
  con la acción `cambiar-tutor`.
- [x] **T2.4 Detalle** con pestañas **Datos / Rotaciones / Historial** y acciones de flujo:
  `cambiar-estado` (Administrador RENADS), `cambiar-tutor` (Universidad). Rotaciones: GET lista +
  POST crear (Universidad) desde la pestaña.
  - **Criterio:** alta/edición/flujo del internado contra el backend; rotaciones listadas/creadas.

## Bloque 3 — Rotaciones (acciones)
- [x] **T3.1 Hooks** `rotations` (lectura) + acciones vía `useFlowAction` con base `rotations`:
  `autorizar` (Autoridad de convenio), `iniciar` (Universidad), `cambiar-estado` (Administrador RENADS),
  `historial` (GET).
- [x] **T3.2 UI** de rotación: en la pestaña Rotaciones del internado (o vista/diálogo de rotación),
  botones gateados por rol + historial (`SimpleObjectTable`). Crear rotación con
  `ipress_origen`/`ipress_destino`/`servicio_area`/fechas/observaciones.
  - **Criterio:** flujo de rotación (crear→autorizar→iniciar) respeta rol y refresca datos.

## Bloque 4 — Verificación
- [x] **T4.1** `npm run lint` y `npm run build` limpios.
- [x] **T4.2** Validador deja `spec/internados.validacion.md` y, si OK, `spec/internados.guia_pruebas.md`.

---

## Criterios de aceptación del módulo (de `docs/mvp.md`)
- Se registra un internado sobre convenio específico vigente; rotaciones con su flujo de autorización.
- CRUD de internos/tutores con alcance/rol.
- Tablas con filtros/paginación del backend; selects desde catálogos reales.

## Decisiones (resueltas)
1. **Pases:** un solo pase (todo el módulo). ✅
2. **Rotaciones:** embebidas en el detalle del internado (diálogos). ✅
3. **`campo_clinico`:** capturado como número (id) por ahora (igual que solicitante); selector
   dependiente del convenio queda pendiente. ✅

## Fuera de alcance
- Documentos/adjuntos; reportes/exportación; tests automatizados.

## Referencias
- Endpoints/campos/roles: `docs/api-internados.md`; roles/alcance: `docs/backend-overview.md`.
- Patrones y stack: `CLAUDE.md`, `docs/frontend-conventions.md`; reutilización de Convenios (arriba).
