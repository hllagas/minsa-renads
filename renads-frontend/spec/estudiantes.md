# Spec — Mejoras UI de la sección Estudiantes (Módulo 2: Internados)

> **✅ APROBADO (2026-09-09) — en `implement`.**
> Decisiones: (P1/P4) los cambios backend los hace este flujo (StudentFilter `nivel_academico` por
> `carrera_profesional__nivel_academico` + `carrera_profesional_detalle`/`especialidad_detalle` en el
> serializer de students); (P2) nivel en el form = **virtual** (solo UI, no persiste); (P3) universidad
> **oculta** vía `fixedValues`; (P7) carga masiva = **avisar + acotar** el selector al alcance (backend
> valida por fila). REQ-BACK-ST-01/02 se implementan aquí; REQ-BACK-ST-03 descartado (nivel virtual).

## Resumen del módulo

Mejoras de UX sobre la sección **Estudiantes** (`students`) del módulo Internados. Afecta a la
página genérica de personas `app/(app)/internados/personas/[entidad]/page.tsx` y a la config
declarativa `PERSON_CONFIGS.students` en `lib/internados/persons.ts`, más el diálogo de carga
masiva `components/internados/students-bulk-upload-dialog.tsx`.

**Pantallas / vistas cubiertas:**
- Listado de estudiantes con **paso previo de elección de universidad** (acotado por alcance).
- Filtro de **nivel académico** (default Pregrado) y columnas rediseñadas.
- Formulario de alta/edición con **universidad bloqueada** y **toggle carrera↔especialidad** por nivel.
- Carga masiva con validación/aviso de alcance institucional.

**Regla de oro:** no romper la ruta compartida con `tutors` (misma página `[entidad]`, mismo
`PERSON_CONFIGS`, mismo `personColumns`, mismo `StudentsBulkUploadDialog` gating). Todos los cambios
deben ser condicionados a `entidad === "students"`.

---

## ⚠️ Hallazgos de contrato (bloqueantes — leer antes de estimar)

Verificado en `lib/api/schema.d.ts` y `docs/api-internados.md`:

1. **`Student` (lectura) NO expone `nivel_academico`.** El schema `Student` (líneas ~7144-7208) y
   `PatchedStudent` (~6517+) tienen `carrera_profesional: number` y `especialidad: number|null`,
   pero **no** existe `nivel_academico` en el estudiante. `nivel_academico` vive en
   `ProfessionalCareerAuto` (la carrera profesional), no en el estudiante.
   → **Impacto:** el requerimiento 1 (filtro `nivel_academico` en el listado de estudiantes) y el
   requerimiento 5 (toggle carrera/especialidad según el `nivel_academico` elegido en el form) **no
   tienen soporte directo** en el contrato actual de `students`. Ver **Preguntas abiertas P1/P2** y
   **REQ-BACK** más abajo. **No inventar el campo.**

2. **El listado `students` NO devuelve campos `*_detalle`.** No hay `carrera_profesional_detalle`,
   `especialidad_detalle` ni `universidad_detalle` en `Student`. Solo ids crudos.
   → **Impacto:** la columna «Carrera profesional» (requerimiento 4) no puede mostrarse por lectura
   directa; hay que resolver el nombre en front (query a `professional-careers`) o pedir `*_detalle`
   al backend. Ver **T3** y **P4 / REQ-BACK**.

3. **`docs/api-internados.md` §students** lista los filtros oficiales como `universidad`,
   `carrera_profesional`, `numero_documento`, `activo`. **No** documenta un filtro
   `nivel_academico`. → Ver **P1 / REQ-BACK**.

4. **«Apellidos y nombres» NO existe como campo del backend.** El `Student` expone `nombres`,
   `apellido_paterno`, `apellido_materno?`. No hay `nombre_completo`. → Se compondrá en el front
   (**T3**), salvo que el usuario pida agregar `nombre_completo` al backend (P5).

> **Nota SDD:** cuando el contrato no soporta un requerimiento, este spec lo marca como pregunta /
> requerimiento al backend, no lo inventa (regla del rol `spec`).

---

## Reglas de negocio de referencia

- **RN-18** — prelación de estudiantes por `nota_promedio_ponderado` (usada por el backend; sin
  endpoint propio). El listado debe **mostrar** la nota (requerimiento 4).
- **RN-19** — `carrera_profesional` y `especialidad` son FK opcionales **validadas por nivel
  académico**: para Pregrado se exige `carrera_profesional` (+ `periodo_academico`); para niveles
  distintos de Pregrado se exige `especialidad`. El toggle del form (requerimiento 5) es la
  materialización UX de esta regla; **la autoridad final es el backend**.
- **RN-16** — carga masiva de estudiantes (`POST /students/bulk-upload/`), alcance validado por fila
  en el backend.
- **RN-24** — (solo tutores) 1 a 2 universidades. No aplica a estudiantes; se cita para no
  confundir la ruta compartida.
- **Alcance institucional por universidad** — `useUniversityScope()` (`lib/auth/scope.ts`) deriva
  `{ ids, singleId, scoped }` de `user.perfiles` (`tipo_entidad === "university"`). El backend es la
  autoridad final del alcance; el gating del front es UX.

---

## Tareas

### Capa: Tipos / contratos

- [x] **T0 — Confirmar contrato de `students` antes de implementar.**
  Releer `docs/api-internados.md` §students y `lib/api/schema.d.ts` (`Student`, `PatchedStudent`,
  filtros del `StudentFilter`). Documentar en el PR/validación:
  - si `students` acepta el filtro `?nivel_academico=<id>` (hoy NO documentado);
  - si el listado expone `carrera_profesional_detalle` / `especialidad_detalle` (hoy NO);
  - si existe `nombre_completo` (hoy NO).
  **Criterio de aceptación:** las respuestas quedan registradas; si alguna es «no», se activa la
  ruta de fallback correspondiente (T1/T3) o el REQ-BACK, sin inventar campos.

---

### Capa: Filtros del listado — nivel académico + default Pregrado (requerimiento 1)

- [x] **T1 — Filtro `nivel_academico` con default «Pregrado» (resuelto en runtime).**
  - Añadir a `studentFilters` (en `lib/internados/persons.ts`) un filtro
    `{ name: "nivel_academico", label: "Nivel académico", type: "select", optionsEndpoint: "academic-levels" }`.
    **Colocarlo antes de `carrera_profesional`.**
  - En la página de estudiantes: resolver el id de «Pregrado» consultando `academic-levels`
    (patrón exacto de `app/(app)/catalogos/entidades/[entidad]/page.tsx` líneas ~59-77:
    `useQuery(["academic-levels", ...])` + `find(nombre incluye "pregrado")`) y pasarlo como
    `initialFilters={{ nivel_academico: String(pregradoId) }}` a `ResourceCrud`.
  - El nombre canónico «Pregrado» se compara por texto **normalizado** (minúsculas, `includes`),
    nunca por id hardcodeado.
  - **Dependencia de contrato (bloqueante):** requiere que `students` acepte `?nivel_academico`.
    Si el backend **no** lo soporta (ver T0/P1), este filtro NO puede funcionar como filtro de
    servidor. En ese caso: **no** añadir el filtro y escalar el **REQ-BACK-ST-01** (añadir
    `nivel_academico` a `StudentFilter`, filtrando por `carrera_profesional__nivel_academico`).
  **Criterio de aceptación:** al abrir Estudiantes, el filtro «Nivel académico» aparece
  preseleccionado en «Pregrado» y el listado ya viene filtrado; el usuario puede cambiarlo o
  limpiarlo. `tutors` no muestra este filtro. Si el backend no soporta el filtro, la tarea queda
  bloqueada por REQ-BACK-ST-01 (documentado, no forzado en el front).

---

### Capa: Vista principal — elegir universidad antes de listar (requerimientos 2 y 3)

- [x] **T2 — Paso previo «elegir universidad» acotado por alcance.**
  Rediseñar `app/(app)/internados/personas/[entidad]/page.tsx` (solo para `entidad === "students"`;
  `tutors` conserva el comportamiento actual):
  - Resolver el alcance con `useUniversityScope()`:
    - **`scoped` con `singleId`** → auto-fijar la universidad (comportamiento actual con
      `fixedValues={{ universidad: singleId }}`); **no** mostrar el paso de selección.
    - **`scoped` con varias (`ids.length > 1`)** → mostrar un selector limitado a esas universidades
      (query a `universities` filtrada por `ids`, o `EntityCombobox` con `optionsParams`/filtrado en
      cliente por `ids`). El usuario debe elegir una **antes** de ver el listado.
    - **no `scoped`** (superusuario / `Administrador RENADS`) → mostrar un selector de **todas** las
      universidades (`universities` completo, `EntityCombobox` con búsqueda server-side).
  - Mientras no haya universidad elegida (en los casos que requieren elección): **no** renderizar
    `ResourceCrud`; mostrar solo el selector con copy claro («Selecciona una universidad para ver sus
    estudiantes»).
  - Una vez elegida, renderizar `ResourceCrud` con
    `fixedValues={{ universidad: <elegida> }}` (bloquea el campo en el form **y** filtra el listado,
    porque `fixedValues` se inyecta en payload y se oculta de filtros/formulario — verificado en
    `components/crud/resource-crud.tsx` líneas 132-136, 243).
  - Ofrecer un control para **cambiar de universidad** (volver al selector) sin recargar la página.
  - El componente del paso previo debe reutilizar `EntityCombobox` (`components/form/entity-combobox.tsx`).
  **Criterio de aceptación:**
  - Usuario con una sola universidad: entra directo al listado ya filtrado (sin paso extra).
  - Usuario con 2+ universidades: ve solo sus universidades en el selector; no ve el listado hasta
    elegir; tras elegir, el listado y el form quedan atados a esa universidad.
  - Admin/superusuario: puede elegir cualquier universidad.
  - `tutors` no cambia.
  - En ningún caso el front asume seguridad: el backend sigue filtrando por alcance.

---

### Capa: Columnas del listado (requerimiento 4)

- [x] **T3 — Rediseñar columnas de estudiantes.**
  Reemplazar `personColumns` (compartida con `tutors`) por una **`studentColumns` específica** (no
  tocar la de tutores). Columnas, en orden:
  1. **Carrera profesional** — resolver el nombre. Preferente: usar
     `carrera_profesional_detalle` si el backend lo expone (hoy NO — ver T0/P4). Fallback si no
     existe: resolver por query a `professional-careers` (mapa `id → nombre`) en la página e
     inyectar el `render` de la columna, o escalar **REQ-BACK-ST-02** para añadir
     `carrera_profesional_detalle` al serializer de `students`.
  2. **Número de documento** — `numero_documento`.
  3. **Apellidos y nombres** — campo combinado, `render`:
     `${apellido_paterno} ${apellido_materno ?? ""} ${nombres}`.filter(Boolean).join(" ")`
     (componer en front — ver P5; no existe `nombre_completo`).
  4. **Nota promedio** — `nota_promedio_ponderado` (string decimal; mostrar «—» si `null`).
  **Criterio de aceptación:** el listado de estudiantes muestra exactamente esas 4 columnas en ese
  orden; «Apellidos y nombres» aparece como una sola columna; la nota se muestra o «—»; la columna
  de carrera muestra el nombre (no el id). `tutors` mantiene sus columnas originales.

---

### Capa: Formulario de alta/edición (requerimientos 5)

- [x] **T4 — Universidad bloqueada en el form.**
  Con `fixedValues={{ universidad }}` de T2, el campo `universidad` ya se **oculta** del formulario
  (comportamiento verificado de `ResourceCrud`). Confirmar con el usuario si «bloqueado» = oculto
  (recomendado, coherente con el flujo) o = **visible pero `disabled`** (usar `FieldConfig.disabled`
  + no depender solo de `fixedValues`). Ver **P3**.
  **Criterio de aceptación:** en alta y edición de estudiante, el usuario no puede cambiar la
  universidad; el valor enviado es siempre la universidad elegida en la vista principal.

- [x] **T5 — Toggle `carrera_profesional` ↔ `especialidad` según nivel académico.**
  - Añadir al form de `students` un campo `nivel_academico`
    (`type: "select", optionsEndpoint: "academic-levels"`), **antes** de `carrera_profesional`.
    **Bloqueante de contrato:** `Student`/`PatchedStudent` **no** aceptan `nivel_academico` hoy
    (T0/P2). Si el backend no lo persiste, el campo debe ser **`virtual`** (excluido del payload,
    solo controla la UI) — o escalar **REQ-BACK-ST-03** para agregar `nivel_academico` al modelo.
    Definir con el usuario (P2).
  - Resolver en la página (patrón `organs`/`professional-careers`) los ids de los niveles y capturar
    en closures:
    - `esPregrado(nivelId)` → nombre normalizado incluye «pregrado».
    - `esPostgradoODoctorado(nivelId)` → nombre incluye «postgrado»/«posgrado» o «doctorado».
  - Inyectar en la config (construida en la página tras `useQuery(academic-levels)`):
    - `carrera_profesional`: `showWhen: (v) => esPregrado(v.nivel_academico)`, `required` solo cuando
      visible; `optionsParamsFrom: (v) => ({ nivel_academico: String(v.nivel_academico) })` para
      filtrar las carreras por el nivel (P6); `resetsOn: ["nivel_academico"]`.
    - `especialidad`: `showWhen: (v) => esPostgradoODoctorado(v.nivel_academico)`,
      `resetsOn: ["nivel_academico"]`.
  - Al ocultarse un campo por `showWhen`, `ResourceCrud`/`resource-form` lo excluye del payload
    (verificado en `FieldConfig.showWhen`).
  **Criterio de aceptación:**
  - Nivel = Pregrado → se ve `carrera_profesional`, se oculta `especialidad`; el payload no incluye
    `especialidad`.
  - Nivel = Postgrado o Doctorado → se ve `especialidad`, se oculta `carrera_profesional`; el payload
    no incluye `carrera_profesional`.
  - Cambiar de nivel resetea el campo dependiente (no queda una carrera de Pregrado seleccionada al
    pasar a Postgrado).
  - El backend sigue validando RN-19 (autoridad final).

---

### Capa: Carga masiva + alcance (requerimiento 6)

- [x] **T6 — Aviso/validación de alcance en la carga masiva.**
  En `components/internados/students-bulk-upload-dialog.tsx`:
  - Recibir por props el alcance (`scoped`, `ids`, universidades autorizadas) y/o la universidad
    elegida en la vista principal.
  - Si el usuario está `scoped`: mostrar en el diálogo las universidades autorizadas y una
    **advertencia UX** de que las filas con `universidad_id` fuera de su alcance **serán rechazadas
    por el backend** (`exigir_ambito`, validación por fila). El backend sigue siendo la autoridad;
    el front **no** parsea el `.xlsx` para bloquear (a confirmar en P7).
  - Reflejar en el resumen de resultado (`creados`/`omitidos`/`errores`) los motivos de rechazo por
    alcance que devuelva el backend (ya se muestran hoy; verificar que el motivo sea legible).
  **Criterio de aceptación:** el diálogo de carga masiva informa al usuario `scoped` de sus
  universidades autorizadas y advierte del rechazo por alcance; el flujo de subida y el resumen de
  errores por fila siguen funcionando; no se rompe el gating de rol existente (solo `Universidad` /
  `Administrador RENADS`). El comportamiento exacto (solo avisar vs. validar en cliente) se define en
  P7 antes de implementar.

---

## Gating por rol (UX; backend = autoridad)

- Escritura y carga masiva: `Universidad`, `Administrador RENADS` (sin cambios — `WRITE` en
  `persons.ts` y `canBulkUpload` en la página).
- Alcance de universidad: derivado de `useUniversityScope()` (no de rol). Superusuario/Admin sin
  perfil de universidad → sin restricción.

---

## Riesgos

- **R1 (alto) — contrato incompleto.** `students` no expone `nivel_academico` ni `*_detalle`. Varios
  requerimientos dependen de decisiones de backend (REQ-BACK-ST-01/02/03). Sin ellas, T1/T3/T5 caen
  a fallbacks de front (resolución por query) o quedan bloqueados. **No inventar campos.**
- **R2 — resolución id-por-nombre de niveles depende de la BD.** «Pregrado»/«Postgrado»/«Doctorado»
  se resuelven por nombre normalizado; si el catálogo `academic-levels` cambia sus nombres, el
  toggle y el default se rompen. Mitigar con comparación tolerante (`includes`) y registrar el
  supuesto.
- **R3 — ruta compartida con `tutors`.** Toda mejora debe condicionarse a `entidad === "students"`.
  No mutar `personColumns`/`studentFilters` compartidos sin separar la config de tutores.
- **R4 — el backend es la autoridad del alcance.** El selector y el aviso de carga masiva son UX; no
  asumir seguridad en el front.
- **R5 — `fixedValues` oculta el campo.** Si el usuario quiere universidad «visible pero
  bloqueada», `fixedValues` no basta (lo oculta); habría que usar `disabled` + otra vía de inyección.
  Ver P3.

---

## Preguntas abiertas (resolver antes de `implement`)

- **P1 — Filtro `nivel_academico` en `students`:** ¿el backend soporta/soportará
  `GET /students/?nivel_academico=<id>` (vía `carrera_profesional__nivel_academico`)? Hoy NO está
  documentado. Si no, ¿se agrega (REQ-BACK-ST-01) o se descarta el filtro?
- **P2 — `nivel_academico` en el estudiante:** ¿el modelo `Student` debe **persistir**
  `nivel_academico` (REQ-BACK-ST-03) o es solo un control de UI (`virtual`) que decide qué FK
  (`carrera_profesional` vs `especialidad`) se envía? Esto define si el campo va o no en el payload.
- **P3 — Universidad «bloqueada»:** ¿oculta (vía `fixedValues`, recomendado) o **visible pero
  `disabled`**? Si visible, hay que ajustar el patrón (no depender solo de `fixedValues`).
- **P4 — Nombre de carrera en el listado:** ¿se pide `carrera_profesional_detalle` al backend
  (REQ-BACK-ST-02) o se resuelve en front con una query a `professional-careers`?
- **P5 — «Apellidos y nombres»:** ¿se compone en front (`apellido_paterno` + `apellido_materno` +
  `nombres`, recomendado) o se pide un `nombre_completo` al backend?
- **P6 — Carreras/especialidades del form filtradas por nivel:** ¿el select `carrera_profesional`
  debe filtrarse por `?nivel_academico=<id>` (soportado: `professional-careers` tiene el filtro), y
  `especialidad` requiere algún filtro por nivel (el catálogo `specialties` no expone
  `nivel_academico`)?
- **P7 — Carga masiva y alcance:** ¿el front solo **avisa** (recomendado; backend valida por fila) o
  debe **parsear el `.xlsx`** y bloquear filas fuera del alcance antes de subir? ¿Debe pre-fijarse la
  universidad elegida en la vista y rechazar `.xlsx` con otras universidades?

---

## Requerimientos al backend (derivados; no bloquean el front hasta confirmarse)

| ID | Bloquea | Descripción |
|----|---------|-------------|
| REQ-BACK-ST-01 | T1 (filtro nivel) | Añadir `nivel_academico` a `StudentFilter` (filtrar por `carrera_profesional__nivel_academico`). Sin esto, el filtro de servidor no es posible. |
| REQ-BACK-ST-02 | T3 (columna carrera) | Exponer `carrera_profesional_detalle` (y opc. `especialidad_detalle`) en el serializer de `students` para poblar el listado sin resolver ids en front. |
| REQ-BACK-ST-03 | T5 (persistir nivel) | (Solo si P2 lo decide) Agregar `nivel_academico` al modelo/serializer `Student` para persistir el nivel elegido. Alternativa: mantenerlo como control de UI (`virtual`). |

---

## Referencias explícitas

- Contrato: `docs/api-internados.md` §«Personas (CRUD)» → `students` (filtros `universidad`,
  `carrera_profesional`, `numero_documento`, `activo`); §«Carga masiva de estudiantes — RN-16»;
  RN-18/RN-19.
- Schema: `lib/api/schema.d.ts` → `Student` (~7144-7208), `PatchedStudent` (~6517+),
  `StudentBulkUpload` (~7210), `ProfessionalCareerAuto.nivel_academico` (~6919).
- Código ancla:
  - `lib/internados/persons.ts` → `PERSON_CONFIGS.students`, `studentFilters`, `personColumns`.
  - `app/(app)/internados/personas/[entidad]/page.tsx` → resolución de alcance + `fixedValues`.
  - `lib/auth/scope.ts` → `useUniversityScope()`.
  - `components/internados/students-bulk-upload-dialog.tsx` → carga masiva.
  - `app/(app)/catalogos/entidades/[entidad]/page.tsx` (líneas ~59-77) → patrón de resolución
    id-por-nombre + `initialFilters` para «Pregrado».
  - `components/crud/resource-crud.tsx` (líneas 45-50, 132-136, 243) → semántica de `fixedValues` /
    `initialFilters`.
  - `lib/crud/types.ts` → `FieldConfig` (`showWhen`, `optionsParamsFrom`, `resetsOn`, `virtual`,
    `disabled`), `FilterConfig`, `ColumnConfig`.
  - `components/form/entity-combobox.tsx` → selector de universidad del paso previo.

---

## Aprobación

- [ ] **Aprobación humana del spec** (obligatoria antes de `implement`). Resolver P1–P7 y decidir
  REQ-BACK-ST-01/02/03.
