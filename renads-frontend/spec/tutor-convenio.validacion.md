# Validación — Feature: TutorConvenio

**Fecha:** 2026-09-26
**Validador:** validator
**Build:** pasó sin errores (confirmado por el usuario antes de esta validación)

---

## Hallazgos

### Prioridad BAJA

**[BAJO] E1 — Label del botón de row action no coincide con el spec**
- Archivo: `app/(app)/internados/personas/[entidad]/page.tsx:301`
- Problema: El spec (E1 y CA-1) especifica `label: "Convenios asignados"`. La implementación usa `label: "Convenios"`.
- Corrección: cambiar `label: "Convenios"` → `label: "Convenios asignados"` en la definición de `rowActions` dentro de `TutorsView`.

### Notas informativas (no bloquean el cierre)

**[INFO] D1 — Solo se resuelve el estado «VIGENTE», no PUBLICADO/SUSCRITO**
- Archivo: `lib/internados/tutor-convenio.ts:137-140`
- El hook `useConvenioEspecificoIds` resuelve un único `vigenteId` (busca "vigente"), igual que el patrón de referencia en `internos/page.tsx`. Los estados PUBLICADO/SUSCRITO son aceptados por el backend como vigentes pero el select del form no los filtra explícitamente. Esto replica el comportamiento existente de `internos/page.tsx` (D1-P1 era pregunta abierta). No es un error; el backend aceptará convenios en esos estados vía POST y los mostrará si coinciden con la búsqueda.

**[INFO] C1 — Filtro de IPRESS por universidad no implementado**
- Archivo: `components/internados/tutor-convenio-dialog.tsx:74-76`
- El spec C1 indica "Filtro: `?universidad={universidad}` (si disponible)". La implementación usa solo `{ es_sede_docente: "true" }`. El spec D1-P3 dejaba esto como pregunta abierta. El backend valida el ámbito al hacer POST (400 si IPRESS no pertenece al convenio), por lo que la UX no es incorrecta, solo muestra más opciones de las estrictamente necesarias.

---

## Estado de tareas

Todas las tareas A1–B6, C1, D1, E1, F1 marcadas como completadas en `spec/tutor-convenio.md`.

---

## Veredicto

El único error encontrado es de **prioridad baja** (label del botón). Todos los criterios de aceptación CA-2 a CA-10 están cubiertos correctamente. CA-1 está cubierto funcionalmente (el botón existe y abre el dialog correcto) pero con label distinto al especificado.

**Recomendación:** corregir el label en `implement` antes de cerrar el feature. No bloquea el funcionamiento pero sí incumple literalmente el spec.
