# Spec — Generación de PDFs de Convenio

> **Estado:** PENDIENTE DE APROBACIÓN HUMANA.
> Este spec NO debe pasarse a `implement` hasta que un humano lo apruebe explícitamente.

## 1. Resumen

Feature incremental sobre el módulo Convenios (base cerrada). Añade dos acciones de generación de
PDF directamente en la página de detalle del convenio (`/convenios/[id]`):

- **«Generar proyecto»** — `POST /conventions/{id}/generar-proyecto/` — renderiza la plantilla
  docxtpl como PDF y lo adjunta con tipo `PROYECTO_CONVENIO` (o `PROYECTO_ADENDA` si es adenda).
- **«Generar expediente»** — `POST /conventions/{id}/generar-expediente/` — concatena (pypdf) el
  proyecto + resoluciones de representantes + resoluciones CONAPRES, adjunta con tipo `EXPEDIENTE`.

Ambas acciones no requieren body. La respuesta `200` devuelve el `Document` creado o versionado
(si ya existía, la versión anterior queda en estado `REEMPLAZADO`; `version` sube en 1).

Archivos que se modifican o crean en este feature:

| Tipo | Ruta |
|------|------|
| Nuevo hook | `lib/convenios/pdf.ts` |
| Modificado | `app/(app)/convenios/[id]/page.tsx` |

---

## 2. Contrato del backend (fuente: `docs/api-convenios.md` §Generación de PDFs)

```
POST /conventions/{id}/generar-proyecto/    body: {} (vacío)   → Document 200
POST /conventions/{id}/generar-expediente/  body: {} (vacío)   → Document 200
```

Respuesta `Document`:
```
id, tipo_documento, tipo_documento_nombre, tipo_contenido, id_objeto,
referencia_externa, nombre_archivo, version, estado, cargado_por, cargado_en
```

Rol: `Administrador RENADS` o `DIGEP`. Ningún otro rol puede ejecutar estas acciones.
La operación puede tardar varios segundos (renderizado + conversión).

---

## 3. Lógica de visibilidad de botones (UX gate)

El estado actual del convenio (`c.estado_codigo`) determina qué botones se muestran:

| Condición de estado | Botón visible |
|--------------------|---------------|
| Estado anterior a `FIRMADO_DIGEP` (excluido) | Solo «Generar proyecto» |
| Estado `FIRMADO_DIGEP` o cualquier estado posterior | Solo «Generar expediente» |

Implementación recomendada: definir una constante local de estados que se consideran
"firmado o posterior" y comparar con `c.estado_codigo`. Los códigos relevantes (de
`convention-statuses`) son, por orden de flujo: `SOLICITUD_REGISTRADA`, `EN_EVALUACION`,
`OBSERVADO`, `VALIDADO`, `EN_OPINION_JURIDICA`, `APROBADO`, `ENVIADO_A_FIRMA`,
`FIRMADO_DIGEP`, `FIRMADO_MINSA`, `FIRMADO_UNIVERSIDAD`, `SUSCRITO`, `PUBLICADO`,
`VIGENTE`, `VENCIDO`, `CERRADO`, `ANULADO`, `AMPLIADO`.

> **Nota al implementador:** si el contrato no especifica los códigos exactos que siguen a
> `FIRMADO_DIGEP`, usar la lista de `convention-statuses` del catálogo en runtime (no
> hardcodear labels, sí códigos). Si los códigos no están disponibles en el objeto del
> convenio o en un catálogo accesible, hacer visible **ambos botones** para los roles
> autorizados y dejar que el backend rechace la operación cuando no corresponda.
> La lógica de visibilidad descrita arriba es UX; la autoridad final es el backend.

---

## 4. Tareas

### Capa API — hook de generación (`lib/convenios/pdf.ts`)

- [x] **T1 — Crear `lib/convenios/pdf.ts`** con los siguientes exports:

  **T1.1 — Tipo `GenerarPdfResult`** (alias de `Documento` de `lib/api/documents.ts` —
  el backend devuelve el mismo shape de `Document`):
  ```ts
  export type GenerarPdfResult = Documento;
  ```

  **T1.2 — Hook `useGenerarProyecto(convenioId: number)`:**
  - Mutation TanStack Query (`useMutation`).
  - `mutationFn`: `POST /conventions/{convenioId}/generar-proyecto/` con body `{}`,
    vía `api.post<GenerarPdfResult>`.
  - `onSuccess`: invalidar `resourceKeys.list("documents")` + invalidar
    `resourceKeys.detail("conventions", convenioId)`.
  - Retorna la mutation con el `GenerarPdfResult` como dato de éxito.

  **T1.3 — Hook `useGenerarExpediente(convenioId: number)`:**
  - Ídem, pero llama `POST /conventions/{convenioId}/generar-expediente/`.
  - Misma invalidación que T1.2.

  **Criterio de aceptación de T1:** TypeScript compila sin errores. Los hooks usan `api`
  de `@/lib/api/client` (no `fetch` ni Axios directo en el componente). La firma
  `mutationFn: async () => { const { data } = await api.post(..., {}); return data; }`.

---

### Componente — botones en la página de detalle

- [x] **T2 — Modificar `app/(app)/convenios/[id]/page.tsx`** para añadir los botones de
  generación de PDF junto al área de acciones de flujo existente.

  **T2.1 — Importar los hooks y utilidades necesarios:**
  - `useGenerarProyecto`, `useGenerarExpediente` de `@/lib/convenios/pdf.ts`.
  - `toast` de `sonner`.
  - `extractApiError` de `@/lib/api/errors`.
  - `Loader2` de `lucide-react` (icono de spinner durante loading).

  **T2.2 — Instanciar los hooks** en el cuerpo del componente `ConvenioDetallePage`:
  ```ts
  const generarProyecto = useGenerarProyecto(id);
  const generarExpediente = useGenerarExpediente(id);
  ```

  **T2.3 — Calcular visibilidad de cada botón:**
  Definir la constante (fuera del componente, nivel de módulo):
  ```ts
  const ESTADOS_FIRMADO_O_POSTERIOR = new Set([
    "FIRMADO_DIGEP", "FIRMADO_MINSA", "FIRMADO_UNIVERSIDAD",
    "SUSCRITO", "PUBLICADO", "VIGENTE", "VENCIDO", "CERRADO", "AMPLIADO",
  ]);
  ```
  En el componente:
  ```ts
  const esFirmadoOPosterior = ESTADOS_FIRMADO_O_POSTERIOR.has(c.estado_codigo);
  const mostrarProyecto = !esFirmadoOPosterior;
  const mostrarExpediente = esFirmadoOPosterior;
  const puedeGenerar = userHasRole(user, "Administrador RENADS", "DIGEP");
  ```

  **T2.4 — Manejadores de acción** (funciones dentro del componente):
  ```ts
  function onGenerarProyecto() {
    generarProyecto.mutate(undefined, {
      onSuccess: (doc) => {
        toast.success(`Proyecto generado: ${doc.nombre_archivo}`, {
          action: {
            label: "Descargar",
            onClick: () => window.open(doc.referencia_externa, "_blank"),
          },
        });
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  function onGenerarExpediente() {
    generarExpediente.mutate(undefined, {
      onSuccess: (doc) => {
        toast.success(`Expediente generado: ${doc.nombre_archivo}`, {
          action: {
            label: "Descargar",
            onClick: () => window.open(doc.referencia_externa, "_blank"),
          },
        });
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }
  ```

  **T2.5 — Renderizado de los botones** en el JSX, dentro del bloque de acciones de flujo
  (junto a los `FlowActionDialog` existentes), condicional a `puedeGenerar`:
  ```tsx
  {puedeGenerar && mostrarProyecto && (
    <Button
      variant="outline"
      onClick={onGenerarProyecto}
      disabled={generarProyecto.isPending}
    >
      {generarProyecto.isPending
        ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Generando…</>
        : "Generar proyecto"}
    </Button>
  )}
  {puedeGenerar && mostrarExpediente && (
    <Button
      variant="outline"
      onClick={onGenerarExpediente}
      disabled={generarExpediente.isPending}
    >
      {generarExpediente.isPending
        ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Generando…</>
        : "Generar expediente"}
    </Button>
  )}
  ```

  **Criterio de aceptación de T2:**
  - Los botones aparecen solo si `userHasRole(user, "Administrador RENADS", "DIGEP")` es
    verdadero; no aparecen para otros roles.
  - Solo uno de los dos botones es visible a la vez, según el estado del convenio.
  - Durante la generación, el botón muestra spinner + texto «Generando…» y queda `disabled`.
  - Al completar con éxito, aparece un toast con el nombre del archivo y un botón «Descargar»
    que abre `referencia_externa` en una nueva pestaña.
  - En caso de error, aparece un toast con el mensaje del error (`extractApiError`).
  - El bloque de acciones de flujo preexistente no se rompe ni se desplaza.

---

### Build y coherencia

- [x] **T3 — Verificar `npm run build` sin errores ni warnings de TypeScript.**
  - No usar `any` explícito; si el tipo de `mutate` exige `undefined` como argumento en
    lugar de `{}`, ajustar la firma (ver nota abajo).
  - No romper el bloque de acciones de flujo existente en la página.
  - No introducir imports no utilizados.

  > **Nota técnica:** `useMutation` de TanStack Query con `mutationFn: async () => ...`
  > (sin parámetros) acepta `mutate(undefined)`. Si se prefiere `mutate({})`, declarar el
  > tipo de variables de la mutation como `void` o `Record<string, never>`.

---

## 5. Criterios de aceptación globales

| # | Criterio |
|---|---------|
| GA-1 | `npm run build` termina con exit 0 sin errores TS ni ESLint. |
| GA-2 | En la página `/convenios/{id}`, un usuario con rol `Administrador RENADS` ve el botón correspondiente al estado actual. |
| GA-3 | Un usuario sin los roles `Administrador RENADS` ni `DIGEP` no ve ningún botón de generación de PDF. |
| GA-4 | Al pulsar «Generar proyecto», el botón muestra loading durante la llamada; al completar aparece toast de éxito con enlace de descarga. |
| GA-5 | Al pulsar «Generar expediente», ídem GA-4. |
| GA-6 | Si el backend responde error (p.ej. 400 o 500), aparece toast de error con el texto devuelto por `extractApiError`. |
| GA-7 | Tras la generación exitosa, la query `documents` del convenio queda invalidada (la lista de documentos en la pestaña correspondiente, si existe, se refrescará). |
| GA-8 | La lógica de visibilidad (T2.3) no hardcodea el estado como string libre en el JSX; usa el Set `ESTADOS_FIRMADO_O_POSTERIOR`. |

---

## 6. Archivos a crear / modificar

| Archivo | Operación | Descripción |
|---------|-----------|-------------|
| `lib/convenios/pdf.ts` | Crear | Hook `useGenerarProyecto` + `useGenerarExpediente` + tipo `GenerarPdfResult` |
| `app/(app)/convenios/[id]/page.tsx` | Modificar | Añadir botones con loading state, gating de rol y visibilidad por estado |

No se crean nuevos componentes standalone (la lógica cabe en la página + el hook). No se
modifican rutas, layouts, ni otros módulos.

---

## 7. Referencias a docs

- Contrato de endpoints: `docs/api-convenios.md` §Generación de PDFs (líneas 125–144).
- Tipo `Documento`: `lib/api/documents.ts` (interfaz `Documento`).
- Patrón de mutation con toast: `components/catalogos/ipress-sede-docente-action.tsx`.
- `extractApiError`: `lib/api/errors.ts`.
- `userHasRole`: `lib/auth/store.ts`.
- Cliente HTTP: `lib/api/client.ts` (instancia `api` de Axios).
- `useResourceAction`: `lib/api/flow.ts` (no se usa directamente aquí — las mutaciones de
  PDF son más simples porque no requieren payload del usuario).

---

> **Este spec requiere aprobación humana antes de pasar al agente `implement`.**
