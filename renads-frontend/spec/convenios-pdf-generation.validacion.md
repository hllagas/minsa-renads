# Validación — Generación de PDFs de Convenio

**Fecha:** 2026-09-26
**Validador:** Validator agent
**Resultado:** CERRADO con observación baja (L-1)

---

## Estado de tareas

| Tarea | Estado | Notas |
|-------|--------|-------|
| T1 — `lib/convenios/pdf.ts` | CUMPLIDA | Tipo, hooks y mutaciones correctos |
| T2 — botones en `[id]/page.tsx` | CUMPLIDA | Set, gating, loading, toast, handlers |
| T3 — build sin errores | CUMPLIDA | `npm run build` exit 0, sin errores TS ni ESLint en archivos nuevos |

---

## Criterios de aceptación globales

| # | Criterio | Resultado |
|---|---------|-----------|
| GA-1 | `npm run build` exit 0 sin errores | PASS — build limpio (Turbopack, 32 rutas) |
| GA-2 | Botón correcto según estado | PASS — `ESTADOS_FIRMADO_O_POSTERIOR` Set + `mostrarProyecto`/`mostrarExpediente` |
| GA-3 | No visible para roles sin permiso | PASS — `userHasRole(user, "Administrador RENADS", "DIGEP")` |
| GA-4 | Loading + toast éxito «Generar proyecto» | PASS — `isPending`, `Loader2`, `toast.success` con acción «Descargar» |
| GA-5 | Loading + toast éxito «Generar expediente» | PASS — ídem GA-4 |
| GA-6 | Toast error con `extractApiError` | PASS — `onError: (e) => toast.error(extractApiError(e))` |
| GA-7 | Invalida query `documents` tras éxito | OBSERVACIÓN (ver L-1) |
| GA-8 | Visibilidad usa Set, no strings hardcodeados en JSX | PASS — Set a nivel de módulo; JSX solo usa booleanos derivados |

---

## Hallazgos

### L-1 — Baja — Invalidación de documentos usa `resourceKeys.list` en lugar de `resourceKeys.all`

**Archivo:** `lib/convenios/pdf.ts:26` y `:50`

**Problema:** Ambos hooks invalidan con:
```ts
qc.invalidateQueries({ queryKey: resourceKeys.list("documents", {}) });
```
Esto produce la clave `["documents", "list", {}]` que solo coincide con la query sin filtros.
Cualquier query de documentos filtrada por `tipo_contenido`/`id_objeto` (como la que usaría una futura pestaña «Documentos» del convenio) NO queda invalidada.

**Convención del proyecto:** todos los demás hooks del proyecto usan `resourceKeys.all(endpoint)` — ver `lib/api/documents.ts:78`, `lib/crud/hooks.ts:46`, `lib/campos-clinicos/hooks.ts:27`.

**Impacto actual:** Ninguno funcional hoy (no existe pestaña de documentos en el detalle del convenio). Sin embargo, romperá el refresco en cuanto se añada esa pestaña.

**Corrección sugerida** (en `lib/convenios/pdf.ts`, líneas 26 y 50):
```ts
// Antes:
qc.invalidateQueries({ queryKey: resourceKeys.list("documents", {}) });
// Después:
qc.invalidateQueries({ queryKey: resourceKeys.all("documents") });
```

---

## Conclusión

El módulo cumple todas las tareas del spec y todos los criterios de aceptación GA-1 a GA-8, con una observación de severidad **baja** (L-1) en el patrón de invalidación de la query `documents`. No hay errores altos ni medios. El módulo se considera **CERRADO** pendiente de corrección oportunista de L-1 en el siguiente ciclo de implement.
