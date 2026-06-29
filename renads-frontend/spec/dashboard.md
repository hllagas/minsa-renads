# Spec — Módulo `dashboard` (Gráficos estadísticos)

Dashboard de indicadores y gráficos de RENADS. **Primer incremento (v1)**: KPIs + 3 gráficos por
módulo. Fuente analizada y **aprobada por humano**: `docs/dashboard-graficos.md` (decisiones
fijadas, lista [v1]/[v2], filtros transversales, orden de implementación, checklist de calidad).
Contrato del backend: `docs/api-convenios.md`, `docs/api-internados.md`, `docs/api-actividades.md`,
`docs/api-auth.md`, `docs/backend-overview.md`. Convenciones/stack: `docs/frontend-conventions.md`,
`CLAUDE.md`.

> **Estado:** ⏳ **PENDIENTE DE APROBACIÓN HUMANA.** Esta lista de tareas debe aprobarla un humano
> **antes** de pasar a Implement (metodología SDD). No escribir código de aplicación hasta entonces.

## Resumen / pantallas

- **Ruta única** `/dashboard` (App Router, dentro de `app/(app)/`): una sola pantalla con barra de
  filtros global + secciones de KPIs, Convenios, Internados y Actividades.
- **Barra de filtros transversal** sincronizada a la URL (deep-linking): rango de fechas, módulo
  (Tabs), tipo, estado, entidad, ámbito geográfico, granularidad temporal.
- **Fila de KPIs** (4 tarjetas) con métrica grande + badge de variación vs. periodo anterior.
- **Gráficos v1**: Convenios `C1, C2, C3` · Internados `I1, I2, I5` · Actividades `A1, A2, A3`.

## Decisiones heredadas de `docs/dashboard-graficos.md` (no re-decidir)

- **Origen de datos = Vía A (agregación en cliente)** para v1. El backend **solo expone listas**
  (`/conventions/`, `/internships/`, `/rotations/`, `/teaching-activities/`) con filtros +
  paginación DRF; **no hay endpoints `/stats/`**. Se agrupa en el front con TanStack Query
  (`select`) / `useMemo`. La Vía B (endpoints agregados) queda para v2.
- **Librería = shadcn charts (Recharts)**. Colores desde tokens `--chart-1..5` ya definidos en
  `app/globals.css`. Dark mode ya integrado (next-themes).
- **Server-state siempre con TanStack Query**; **Axios solo dentro de `lib/api/`**; **Zustand** solo
  para estado de cliente/UI (los filtros viven en la URL, no en Zustand). UI en español, código en
  inglés, **claves del API en español sin traducir** (`estado_codigo`, `fecha_solicitud`, ...).
- **Un módulo a la vez**: este spec cubre **solo lo marcado [v1]**.

## Alcance institucional (de `docs/api-auth.md` / `backend-overview.md`)

- Todos los listados aplican **alcance institucional** en el backend según `me.perfiles`
  (universidad, IPRESS, ...). El front **no** filtra por alcance: cada gráfico muestra lo que el
  backend devuelve para el usuario. Superusuario y `Administrador RENADS` ven todo.
- **Gating de UI (UX, no seguridad):** el dashboard es visible para cualquier usuario autenticado.
  La visibilidad de las pestañas por módulo se alinea con los roles del menú (`AppShell.NAV_ITEMS`):
  Convenios → `Administrador RENADS, DIGEP, CONAPRES, OGAJ, Secretaría General`; Internados →
  `Administrador RENADS, Universidad, Autoridad de convenio`; Actividades → `Administrador RENADS,
  Universidad, Tutor, Sede docente`. La autoridad final es el backend.

---

## Bloque 0 — Infraestructura del dashboard

- [x] **T0.1 Dependencia `recharts` + wrapper `components/ui/chart.tsx`.** Instalar `recharts` y
  añadir el wrapper shadcn de charts (`ChartContainer`, `ChartTooltip`, `ChartTooltipContent`,
  `ChartLegend`, `ChartLegendContent`, tipo `ChartConfig`). Mapear los colores a
  `var(--color-chart-1)`…`var(--color-chart-5)` (ya expuestos en `globals.css`).
  - **Criterio:** un gráfico de prueba Recharts renderiza dentro de `ChartContainer`, toma color de
    los tokens y respeta dark mode sin estilos extra.
- [x] **T0.2 Componentes shadcn faltantes para el rango de fechas.** Añadir `components/ui/popover.tsx`
  y `components/ui/calendar.tsx` (shadcn; el calendario usa `react-day-picker`) **si no existen**.
  Luego crear `components/dashboard/date-range-picker.tsx` (`DateRangePicker`): Popover + Calendar en
  modo rango, formato `es-PE`, con preajustes ("Últimos 30 días", "Este año", "Todo").
  - **Criterio:** el control devuelve `{ desde, hasta }` como `string` ISO (`yyyy-MM-dd`) o `null`;
    teclado/lector de pantalla operables; cierra al elegir el segundo extremo.
- [x] **T0.3 Filtros globales sincronizados a la URL.** Hook `useDashboardFilters`
  (`lib/dashboard/use-dashboard-filters.ts`) que lea/escriba el querystring con
  `useSearchParams`/`useRouter` (App Router). Estado: `desde`, `hasta`, `modulo`
  (`convenios|internados|actividades`), `tipo`, `estado`, `entidad`, `ambito`, `granularidad`
  (`dia|mes|anio`). Valores vacíos se omiten de la URL. Componente
  `components/dashboard/dashboard-filters.tsx` con los controles: `DateRangePicker`, `Tabs` (módulo),
  `Select` (tipo), `Select` (estado, poblado por catálogo), `Combobox`/`entity-combobox` (entidad),
  `Select` (ámbito, catálogo `health-geographic-scopes`), `Select` (granularidad).
  - **Criterio:** cambiar un filtro actualiza la URL; recargar/compartir la URL restaura el estado;
    los gráficos reaccionan al cambio sin recargar la página.
- [x] **T0.4 Helpers de agregación en cliente** (`lib/dashboard/aggregation.ts`, funciones puras):
  - `countBy(items, keyFn)` → `{ key, count }[]` (group-by por estado/tipo).
  - `sumBy(items, keyFn, valueFn)` → `{ key, total }[]` (p. ej. suma `carga_horaria`).
  - `timeSeries(items, dateFn, granularidad)` → `{ bucket, count }[]` ordenado, con buckets vacíos
    rellenados dentro del rango (sin huecos en el eje X). Soporta `dia|mes|anio`.
  - `timeSeriesByGroup(items, dateFn, groupFn, granularidad)` → series multi-grupo (para A2).
  - **Criterio:** funciones puras, sin dependencias de React; cubren los 4 patrones que piden los
    gráficos v1; manejan listas vacías devolviendo `[]` (no `undefined`).
- [x] **T0.5 Carga completa de listas para la Vía A** (`lib/dashboard/fetch-all.ts`): helper
  `fetchAllPages(endpoint, params)` que recorra la paginación DRF (`next`/`?page=N`) acumulando
  `results`, con **tope de seguridad** (p. ej. máx. N páginas / filas) y aviso de truncamiento.
  Reutiliza `api`/`Paginated` de `lib/api/client.ts` (Axios solo aquí) y `buildListParams` de
  `lib/api/query.ts`. **Pregunta abierta (ver §Contrato):** confirmar si el backend acepta
  `page_size` para reducir nº de peticiones.
  - **Criterio:** devuelve todas las filas dentro del rango filtrado o se detiene en el tope
    señalando que los datos están truncados (para mostrar aviso en la UI).
- [x] **T0.6 Hooks de datos del dashboard** (`lib/dashboard/hooks.ts`, `"use client"`): por cada
  gráfico/KPI un hook TanStack Query que llame a `fetchAllPages` con los filtros relevantes y haga la
  agregación en `select` (memoizada). Keys de query namespaced (`["dashboard", <grafico>, params]`)
  para invalidación/aislamiento. Catálogos de etiquetas (estados/tipos/ámbitos) cargados con
  `staleTime` largo y reutilizando los hooks de catálogo existentes por módulo
  (`lib/convenios/*`, `lib/internados/*`, `lib/actividades/*`); **no hardcodear nombres** de estados.
  - **Criterio:** cada hook expone `{ data, isLoading, isError, refetch }`; ningún componente usa
    `fetch`/Axios directo; los labels de estado/tipo salen del catálogo, no de strings fijos.
- [x] **T0.7 Ruta y armazón de la pantalla.** Crear `app/(app)/dashboard/page.tsx` (`"use client"`)
  que componga: `DashboardFilters` + secciones KPIs / Convenios / Internados / Actividades. Añadir
  ítem `Dashboard` a `AppShell.NAV_ITEMS` (`roles: []`, visible a todo autenticado). Componentes
  compartidos `components/dashboard/chart-card.tsx` (envoltura `Card` con título, descripción,
  estados de **skeleton**, **vacío** "Sin datos" y **error + reintento**).
  - **Criterio:** `/dashboard` carga tras login; el menú lo muestra; cada gráfico se monta dentro de
    `ChartCard` con sus tres estados (carga/vacío/error) disponibles.

## Bloque 1 — Tipos / contratos

- [x] **T1.1 Reutilizar tipos generados de OpenAPI** (`lib/api/schema.d.ts`): `ConventionRead`,
  `InternshipRead`, `RotationRead`, `TeachingActivityRead` (ya disponibles desde los módulos previos).
  **No tipar a mano** las respuestas. Definir solo tipos locales del dashboard en
  `lib/dashboard/types.ts`: `DashboardFilters`, `CountBucket`, `SumBucket`, `TimeBucket`,
  `TimeSeriesGroup`, `KpiCard`. Claves del API en español, intactas.
  - **Criterio:** cero `any`; los buckets y filtros tienen tipos explícitos; `tsc --noEmit` limpio.

## Bloque 2 — KPIs (`docs/dashboard-graficos.md` §3.1) `[v1]`

- [x] **T2.1 Hook de KPIs** (`lib/dashboard/hooks.ts`): calcular las 4 métricas dentro del rango de
  fechas activo y la **variación vs. periodo anterior** (mismo nº de días inmediatamente anterior):
  1. **Convenios vigentes** — `GET /conventions/`; contar `estado_codigo === "VIGENTE"`.
  2. **Internados activos** — `GET /internships/`; contar el `estado_codigo` de "en curso/activo"
     (resolver el código desde el catálogo `internship-statuses` — ver §Contrato).
  3. **Actividades validadas** — `GET /teaching-activities/`; contar `estado_codigo === "VALIDADA"`
     y su **% sobre el total** del rango.
  4. **Carga horaria total** — `GET /teaching-activities/`; sumar `carga_horaria` en el rango
     (`fecha_actividad`).
  - **Criterio:** los 4 valores se calculan client-side (Vía A) y reflejan el rango filtrado; la
    variación compara contra el periodo anterior equivalente; números en formato `es-PE`.
- [x] **T2.2 Tarjetas KPI** (`components/dashboard/kpi-cards.tsx`): 4 `Card` con métrica grande +
  `Badge` de variación (↑/↓ con texto, **no solo color**) + skeleton por tarjeta + estado vacío.
  - **Criterio:** responsive (1→2→4 columnas); badge accesible (texto + icono + color); skeleton
    mientras carga; "—" si no hay datos.

## Bloque 3 — Convenios (`§3.2`) `[v1]`

Origen común: `GET /conventions/` (filtros `ConventionFilter`). Etiquetas de estado desde el
catálogo `convention-statuses`; tipos desde `convention-types`.

- [x] **T3.1 C1 — Convenios por estado** · **BarChart horizontal**. Conteo por `estado_codigo`
  (etapas del flujo, ordenadas). Filtros: `tipo_convenio`, rango `fecha_solicitud`. Agregación:
  `countBy(estado_codigo)`.
  - **Criterio:** una barra por estado presente, ordenada por etapa del flujo; tooltip con valor
    exacto; etiquetas legibles del catálogo (no códigos crudos); barras horizontales en móvil.
- [x] **T3.2 C2 — Marco vs. Específico** · **PieChart (donut)**. Proporción por `tipo_convenio`
  (2 categorías). Filtros: rango de fechas. Agregación: `countBy(tipo_convenio)`.
  - **Criterio:** donut con ≤2 segmentos, leyenda + % en tooltip; etiqueta textual por segmento.
- [x] **T3.3 C3 — Solicitudes en el tiempo** · **AreaChart**. Serie de `fecha_solicitud` agrupada por
  la **granularidad** activa (`dia|mes|anio`). Filtros: `tipo_convenio`, `estado` (`estado_actual`).
  Agregación: `timeSeries(fecha_solicitud, granularidad)`.
  - **Criterio:** eje X rotulado con la granularidad; sin huecos (buckets vacíos = 0); tooltip por
    punto; respeta `prefers-reduced-motion`.

## Bloque 4 — Internados (`§3.3`) `[v1]`

Orígenes: `GET /internships/` (`InternshipFilter`) y `GET /rotations/`. Etiquetas desde
`internship-statuses` y `rotation-statuses`.

- [x] **T4.1 I1 — Internados por estado** · **BarChart horizontal**. Conteo por `estado_codigo`.
  Filtros: `convenio`, `ambito_geografico_sanitario`. Agregación: `countBy(estado_codigo)`.
  - **Criterio:** una barra por estado del catálogo `internship-statuses`; tooltip con valor exacto;
    responsive.
- [x] **T4.2 I2 — Altas de internados en el tiempo** · **AreaChart**. Serie de `fecha_inicio`
  agrupada por **mes** (o granularidad activa). Filtros: `ambito_geografico_sanitario`.
  Agregación: `timeSeries(fecha_inicio, granularidad)`.
  - **Criterio:** eje temporal rotulado; buckets vacíos = 0. **Nota/Contrato:** el filtro
    `universidad` que sugiere `docs/dashboard-graficos.md` **no existe** en `InternshipFilter`
    (solo en `interns`); el filtro de universidad se difiere/omite hasta resolver (§Contrato).
- [x] **T4.3 I5 — Rotaciones por estado** · **BarChart**. Conteo por `estado_codigo` de rotaciones
  (`SOLICITADA`, `AUTORIZADA`, `OBSERVADA`, `RECHAZADA`, `EN_CURSO`, ...). Filtros: `ipress_origen` /
  `ipress_destino`, `servicio_area` (nombres reales del filtro de `rotations`; el doc dice "ipress").
  Agregación: `countBy(estado_codigo)`.
  - **Criterio:** una barra por estado del catálogo `rotation-statuses`; etiquetas legibles; tooltip
    exacto; el filtro de IPRESS usa `ipress_origen`/`ipress_destino` (no `ipress`).

## Bloque 5 — Actividades (`§3.4`) `[v1]`

Origen: `GET /teaching-activities/` (`TeachingActivityFilter`). Etiquetas desde `activity-statuses`
y `activity-types`.

- [x] **T5.1 A1 — Actividades por estado** · **PieChart (donut)**. Proporción por `estado_codigo`
  (`REGISTRADA`, `VALIDADA`, `OBSERVADA`, `SUBSANADA`, `RECHAZADA`, ...). Filtros: `tipo_actividad`,
  `tutor`. Agregación: `countBy(estado_codigo)`.
  - **Criterio:** donut con etiqueta + % por estado; si hay >5 categorías, agrupar el resto en
    "Otros" para mantener legibilidad; leyenda visible.
- [x] **T5.2 A2 — Actividades en el tiempo** · **AreaChart multi-serie por estado**. Serie de
  `fecha_actividad` agrupada por **semana/mes** (granularidad activa), una serie por `estado_codigo`.
  Filtros: `tipo_actividad`, `ipress`. Agregación: `timeSeriesByGroup(fecha_actividad, estado_codigo,
  granularidad)`.
  - **Criterio:** áreas apiladas por estado con colores `--chart-1..5`; leyenda conmutable; tooltip
    con desglose por estado; sin huecos en el eje.
- [x] **T5.3 A3 — Carga horaria por tipo de actividad** · **BarChart**. Suma de `carga_horaria` por
  `tipo_actividad`. Filtros: rango `fecha_actividad`, `ipress`. Agregación:
  `sumBy(tipo_actividad, carga_horaria)`.
  - **Criterio:** una barra por tipo (etiqueta de `activity-types`); eje Y en horas con formato
    `es-PE`; tooltip con total exacto.

## Bloque 6 — Calidad / UX transversal (checklist `docs/dashboard-graficos.md` §5)

- [x] **T6.1** Cada gráfico cumple: tipo acorde al dato, leyenda + tooltip con valor exacto, skeleton
  de carga, estado vacío ("Sin datos" + guía, nunca eje en blanco) y estado de error con reintento.
  - **Criterio:** los 4 KPIs y los 9 gráficos pasan el checklist; revisado en `validacion.md`.
- [x] **T6.2** Accesibilidad y formato: color **nunca** como único indicador (etiqueta/icono),
  contraste de datos ≥3:1, números `es-PE`, fechas con granularidad rotulada, responsive sin scroll
  horizontal (barras horizontales / menos ticks en móvil), `prefers-reduced-motion` respetado.
  - **Criterio:** verificable en desktop y móvil, claro y oscuro.

---

## Contrato — preguntas abiertas (no inventar; resolver antes/durante Implement)

1. **Semántica del filtro de estado.** Los filtros se llaman `estado_actual` (convenios/internados)
   y `estado_actual` (actividades), mientras que las lecturas exponen `estado_actual` (nombre) y
   `estado_codigo` (código). ¿El filtro acepta **código**, **nombre** o **id**? Mientras se aclara,
   la Vía A **agrega por `estado_codigo` en el cliente** y evita depender del filtro de estado para
   los conteos.
2. **`page_size`.** `backend-overview.md` fija `PAGE_SIZE=20` y solo documenta `?page=N`. ¿Se admite
   `?page_size=` para reducir el nº de peticiones de la Vía A? Si no, `fetchAllPages` paginará con
   tope de seguridad.
3. **I2/I4 por universidad.** `InternshipFilter` **no** expone `universidad` (solo `interns`). El
   filtro de universidad en I2 queda fuera hasta que el backend lo exponga o se cruce vía `interno`.
4. **I5 IPRESS.** `rotations` filtra por `ipress_origen`/`ipress_destino` (no `ipress`); el filtro de
   entidad para I5 debe mapear a esos campos.
5. **Códigos "activo/en curso".** El KPI "Internados activos" requiere el `estado_codigo` exacto que
   representa "en curso" en `internship-statuses` (p. ej. `EN_CURSO`/`ACTIVO`); cargar el catálogo y
   confirmar el código real, sin hardcodear.
6. **Sin endpoints `/stats/`.** Confirmado por las docs: v1 es Vía A (cliente). Registrar en paralelo
   el requerimiento de endpoints agregados al equipo backend (tarea de coordinación, no de código).

## Fuera de alcance — `[v2]` (NO implementar en este incremento)

- **Convenios:** `C4` Próximos a vencer · `C5` Top entidades solicitantes · `C6` Campos clínicos por
  especialidad.
- **Internados:** `I3` Internados por IPRESS · `I4` Internados por universidad · `I6` Rotaciones por
  interno (RN-9).
- **Actividades:** `A4` Carga horaria por servicio/área · `A5` Tasa de validación por tutor ·
  `A6` Embudo de validación.
- **Infraestructura v2:** migración a **Vía B** (endpoints `/<recurso>/stats/?group_by=…`), export
  CSV en tablas pesadas, y demás controles compuestos (Bar list / BadgeDelta) no requeridos en v1.

---

> **Recordatorio SDD:** esta lista requiere **aprobación humana** antes de Implement. El Validator
> marcará los checkboxes `[ ] → [x]` y generará `spec/dashboard.validacion.md` al cerrar el módulo.
