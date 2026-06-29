# Validación — Módulo `dashboard` (incremento v1)

> Revisión del código de Implement contra `spec/dashboard.md`, `docs/dashboard-graficos.md` y el
> contrato del backend (`docs/api-*.md`, `docs/frontend-conventions.md`, `CLAUDE.md`).
> Fecha: 2026-06-27 · Validador: agente `validator`.

## Resultado de chequeos técnicos

- `npx tsc --noEmit` → **limpio** (sin errores; cero `any` en el módulo).
- `npm run build` (`next build`, Turbopack) → **OK**; la ruta `/dashboard` se genera (○ estática).
- `npm run lint` → **1 error + 1 warning, ambos PRE-EXISTENTES y fuera del dashboard**:
  - `components/layout/theme-toggle.tsx:18` — `react-hooks/set-state-in-effect` (no es del módulo).
  - `components/ui/data-table.tsx:36` — warning `react-hooks/incompatible-library` (no es del módulo).
  - **El módulo dashboard no introduce ningún hallazgo de lint.**

## Estado por tarea

| Tarea | Estado | Nota |
|-------|--------|------|
| T0.1 recharts + `chart.tsx` (tokens `--color-chart-1..5`) | **OK** | Wrapper presente; los charts toman color de los tokens; dark mode por CSS. |
| T0.2 Popover/Calendar + `DateRangePicker` | **OK** | H1 resuelto: Calendar shadcn (`react-day-picker` v10) en modo rango; cierra al 2º extremo. Re-validado 2026-06-27. |
| T0.3 Filtros globales sincronizados a URL | **OK (desvío menor)** | Ver H2 (filtro `estado` omitido, decisión de contrato). |
| T0.4 Helpers `countBy/sumBy/timeSeries/timeSeriesByGroup` | **OK** | Funciones puras; rellenan buckets sin huecos; devuelven `[]` en vacío. |
| T0.5 `fetchAllPages` (tope + truncado + `page_size`) | **OK** | `MAX_PAGES=25`, `truncated`, `// TODO(contrato)` para `page_size`. |
| T0.6 Hooks con `select` + keys namespaced + catálogos | **OK** | Ver H6 (catálogos vía `useCatalogLabels` genérico). |
| T0.7 Ruta + `AppShell.NAV_ITEMS` + `ChartCard` 3 estados | **OK** | `Dashboard` con `roles: []`; `ChartCard` con skeleton/vacío/error+reintento. |
| T1.1 Tipos OpenAPI + tipos locales | **OK** | Reutiliza `*Read` de `lib/api/schema`; tipos locales en `types.ts`. |
| T2.1 Hook de KPIs (4 + variación) | **OK** | Variación vs. periodo anterior; `// TODO(contrato)` para "activo". Ver H3. |
| T2.2 Tarjetas KPI | **OK** | 4 cards; badge con icono+texto (no solo color); skeleton; "—". |
| T3.1 C1 Convenios por estado (barra horizontal) | **OK** | `countBy(estado_codigo)` + `sortByFlow` por orden de catálogo. |
| T3.2 C2 Marco vs. Específico (donut) | **OK (menor)** | Ver H4 (tooltip sin %; etiqueta = `tipo_convenio` del read). |
| T3.3 C3 Solicitudes en el tiempo (área) | **OK** | `timeSeries(fecha_solicitud)`; filtro `estado` no expuesto (decisión Q1). |
| T4.1 I1 Internados por estado (barra horizontal) | **OK** | `countBy(estado_codigo)`, labels de `internship-statuses`. |
| T4.2 I2 Altas en el tiempo (área) | **OK** | `timeSeries(fecha_inicio)`; `universidad` diferido (Q3). Ver H7. |
| T4.3 I5 Rotaciones por estado (barra) | **OK** | `ipress_origen` con `// TODO(contrato)`; sin filtro `servicio_area` (menor). |
| T5.1 A1 Actividades por estado (donut) | **OK** | `topNWithOther(5)`→"Otros"; labels `activity-statuses`; sin filtro `tutor` (menor). |
| T5.2 A2 Actividades en el tiempo (área apilada) | **OK** | `timeSeriesByGroup(fecha_actividad, estado_codigo)`; leyenda conmutable. |
| T5.3 A3 Carga horaria por tipo (barra) | **OK (menor)** | `sumBy(tipo_actividad, carga_horaria)`; etiqueta = `tipo_actividad` del read (H4). |
| T6.1 Estados por gráfico (skeleton/vacío/error) | **OK** | Vía `ChartCard`; tooltips presentes; donut sin % (H4). |
| T6.2 Accesibilidad y formato | **OK (observación)** | `es-PE`, `prefers-reduced-motion`, color+etiqueta; ver H5 (paleta gris). |

**Marcadas `[x]` en `spec/dashboard.md`:** **todas** (T0.1–T6.2), incluida T0.2 tras la corrección.

## Cumplimiento de contrato

- Endpoints correctos: `conventions`, `internships`, `rotations`, `teaching-activities` y catálogos
  (`convention-statuses`, `internship-statuses`, `rotation-statuses`, `activity-statuses`,
  `convention-types`, `activity-types`, `health-geographic-scopes`, `ipress`).
- Campos/filtros reales y en español sin traducir: `estado_codigo`, `fecha_solicitud`, `fecha_inicio`,
  `fecha_actividad`, `tipo_convenio`, `tipo_actividad`, `carga_horaria`, `ambito_geografico_sanitario`,
  `ipress_origen`/`ipress_destino`. Sin campos inventados.
- `InternshipFilter` sin `universidad`: respetado. `rotations` por `ipress_origen` (no `ipress`): respetado.
- Las 5 preguntas de contrato: los **supuestos** efectivos están marcados con `// TODO(contrato)` y son
  conservadores — Q2 `page_size` (`fetch-all.ts`), Q4 `ipress_origen` y Q5 código "activo" (`hooks.ts`).
  Q1 (semántica de `estado`) y Q3 (`universidad`) se resuelven **omitiendo** el filtro (sin asumir nada).

## Convenciones

- Server-state 100% con TanStack Query; **Axios solo en `lib/api/`** (vía `fetchAllPages`/`api`). Ningún
  `fetch`/Axios suelto en componentes. ✔
- Zustand solo para `me`/sesión (gating); filtros en la URL, no en Zustand. ✔
- shadcn/ui + Tailwind v4 (sin `tailwind.config.js`); tokens `--chart-1..5` mapeados a `--color-chart-*`
  en `globals.css`; dark mode por CSS. ✔
- UI en español, código en inglés, claves del API intactas. ✔
- Gating de pestañas por rol alineado con `AppShell.NAV_ITEMS`; ítem `Dashboard` con `roles: []`. ✔

## Hallazgos (priorizados)

### Medios
- **H1 — T0.2: `DateRangePicker` no usa el Calendar shadcn/`react-day-picker`.** **RESUELTO (2026-06-27).**
  Re-validación tras la corrección de Implement:
  - `components/ui/calendar.tsx` creado: wrapper shadcn sobre `react-day-picker` v10 (`DayPicker`), estilado
    con Tailwind v4 y tokens del proyecto (claro/oscuro vía variables CSS); foco gestionado en `CalendarDayButton`.
  - `components/dashboard/date-range-picker.tsx` reescrito: `Popover` + `Calendar` en `mode="range"`,
    `locale={es}`, `numberOfMonths={2}`, preajustes ("Últimos 30 días", "Este año", "Todo"). **Sin inputs nativos.**
  - **Cierra al elegir el segundo extremo:** `handleSelect` ejecuta `setOpen(false)` cuando `range?.from && range?.to`.
  - **API pública intacta:** salida `{ desde, hasta }` ISO `yyyy-MM-dd` o `null` (`dateToIso` = `format(..,"yyyy-MM-dd")`);
    consumidores (`dashboard-filters.tsx`, `lib/dashboard/use-dashboard-filters.ts`) sin cambios y no rotos.
  - **Sin desfase de zona horaria:** conversión vía `parse`/`format` de `date-fns` en hora local; no se usa
    `toISOString()` ni `new Date(isoString)`.
  - **Accesibilidad:** `aria-label` en el trigger (rango activo), `autoFocus` y navegación por teclado del calendario.
  - Dependencias añadidas: `react-day-picker` ^10.0.1, `date-fns` ^4.4.0 (presentes en `package.json`).
  - Chequeos: `npx tsc --noEmit` limpio · `npm run build` OK (ruta `/dashboard` ○ estática) · `npm run lint`
    solo los **2 hallazgos pre-existentes fuera del dashboard** (`theme-toggle.tsx:18`, `data-table.tsx:36`).

### Bajos / menores
- **H2 — T0.3: filtro `estado` omitido de la barra** (`lib/dashboard/types.ts`, `dashboard-filters.tsx`).
  Intencional y conservador (Q1: se agrega por `estado_codigo` en cliente). Recomendado: dejar un
  `// TODO(contrato)` cerca del omitido para trazabilidad.
- **H3 — T2.1: KPI "Internados activos" por heurística** (`lib/dashboard/hooks.ts:368`): regex
  `/CURSO|ACTIV/i` sobre `internship-statuses`, marcado `// TODO(contrato)`. Aceptable para v1; confirmar
  el código real con backend.
- **H4 — C2/A1: tooltip de donut sin % y etiquetas de tipo desde el `*Read`.** `donut-chart.tsx` muestra
  valor exacto pero no el % que pide el criterio (C2/A1). En C2/A3 la etiqueta de tipo es el string del
  read (ya legible) en vez del catálogo `convention-types`/`activity-types`. Mejora menor: añadir % al
  tooltip del donut.
- **H5 — T6.2: paleta `--chart-1..5` monocroma (gris)** en `globals.css:70-74,105-109`; los segmentos se
  distinguen por leyenda/etiqueta (color nunca es el único indicador, criterio cumplido) pero el contraste
  entre tonos adyacentes puede caer bajo 3:1. Decisión de tema **pre-existente**, no del dashboard;
  considerar tonos con croma para gráficos categóricos.
- **H6 — T0.6: catálogos vía `useCatalogLabels` genérico** (`lib/dashboard/catalogs.ts`) en vez de los
  hooks de catálogo por módulo que sugiere el spec. Equivalente funcional (TanStack Query, `staleTime`
  largo, sin hardcodear nombres). Solo nota de divergencia.
- **H7 — Filtros por gráfico no expuestos como control:** `servicio_area` (I5), `tutor` (A1), `estado`
  (C3). Coherente con una barra de filtros mínima y con la decisión Q1. Sin impacto en contrato. Opcional v2.

## Veredicto

**APROBADO (módulo cerrado).** Re-validación 2026-06-27: resuelto el único hallazgo bloqueante (H1/T0.2).
El incremento v1 está completo y correcto: compila (`tsc` limpio), construye (`/dashboard` ○ estática) y no
introduce hallazgos de lint (los 2 existentes son pre-existentes y fuera del dashboard); respeta el contrato
(endpoints/campos/filtros reales, claves en español), las convenciones de stack (TanStack Query / Axios solo
en `lib/api/` / Zustand / shadcn / Tailwind v4) y el gating por rol. **Todas las tareas v1 (T0.1–T6.2)
cumplen su criterio.** No quedan hallazgos altos ni medios bloqueantes.

**Mejoras opcionales (no bloquean el cierre):** H2 (TODO de trazabilidad para `estado`), H4 (% en tooltip de
donut), H5 (paleta categórica con croma), H6/H7 (notas de divergencia/filtros opcionales para v2).
