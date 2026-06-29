# Dashboard — Gráficos estadísticos

> Lista de gráficos propuestos para el dashboard de RENADS, con filtros transversales
> (rango de fechas, tipo, estado, entidad, ámbito geográfico). **Decisiones ya tomadas** (abajo).
> Pendiente de aprobación final humana antes de pasar a `spec/dashboard.md` (metodología SDD).

## Decisiones fijadas

- **Origen de datos:** **Híbrido A→B**. Arrancar con agregación en cliente (vía A) para v1;
  migrar a endpoints `/stats/` del backend (vía B) cuando el volumen lo exija.
- **Alcance v1:** **KPIs + 3 gráficos por módulo** → `C1, C2, C3` · `I1, I2, I5` · `A1, A2, A3`.
  El resto (marcados *v2*) queda fuera del primer spec.
- **Librería:** **shadcn charts (Recharts)** — ver evaluación en §1.

## 0. Origen de los datos agregados (vía A → B)

El backend **solo expone endpoints de lista** (`/conventions/`, `/internships/`, `/rotations/`,
`/teaching-activities/`) con filtros + paginación DRF. **No hay endpoints de agregación**.

- **v1 — Vía A (cliente):** TanStack Query pide la lista filtrada y se agrupa en el front
  (por estado, mes, tipo…). Para mantener exactitud sin traer miles de filas: pedir `page_size`
  acotado al rango filtrado y agrupar en un `select`/`useMemo`. Aceptable para volúmenes bajos.
- **v2 — Vía B (backend):** solicitar a `renaes-api` endpoints `/<recurso>/stats/?group_by=…`
  que devuelvan ya agregado (mejor rendimiento, exactitud y respeto del alcance institucional).
  Registrar el requerimiento al equipo backend en paralelo a v1.

## 1. Evaluación de librería: shadcn charts vs. Tremor Raw

| Criterio | **shadcn charts** (elegido) | Tremor Raw | @tremor/react (legacy) |
|----------|------------------------------|------------|------------------------|
| Tailwind v4 CSS-only | ✅ nativo | ✅ | ❌ exige Tailwind v3 + config JS |
| Coherencia con el proyecto | ✅ ya usamos shadcn (`components/ui/`) | parcial | ❌ |
| Dark mode (next-themes ya integrado) | ✅ por tokens CSS | ✅ | ⚠️ tokens propios |
| Base | Recharts + `ChartContainer`/`ChartTooltip` | Recharts + Radix | Recharts (v3) |
| Componentes de dashboard listos | medios (se componen) | más (BarList, Tracker…) | más |

**Decisión: shadcn charts.** Encaja sin fricción con Tailwind v4, el patrón shadcn existente y el
dark mode ya integrado; los colores salen de los tokens `--chart-1..5` ya definidos en
`app/globals.css`. Lo que Tremor da "gratis" (BarList, BadgeDelta) se compone a mano con Recharts +
componentes shadcn ya presentes (`Card`, `Badge`, `Progress`). Descartado `@tremor/react` legacy
(rompería el patrón Tailwind v4 CSS-only).

> Acción de setup: añadir `components/ui/chart.tsx` (wrapper shadcn de Recharts) + dependencia
> `recharts`. Mapear `--color-chart-1..5` en la config de chart.

Server-state siempre vía **TanStack Query** (no fetch suelto). Cliente HTTP en `lib/api/`.

## 2. Filtros transversales del dashboard

Barra de filtros global (afecta a todos los gráficos), **sincronizada a la URL** (querystring)
para deep-linking y preservación de estado. Controles con componentes ya existentes:

| Filtro | Control (componente del repo) | Mapea a (API) |
|--------|-------------------------------|---------------|
| Rango de fechas | `DateRangePicker` (nuevo: Popover + Calendar) | rangos `fecha_*` de cada recurso |
| Módulo / sección | `Tabs` (`components/ui/tabs`) | recurso destino |
| Tipo de convenio | `Select` (`components/ui/select`) | `tipo_convenio` |
| Estado | `Select` (catálogo) | `estado_actual`/`estado_codigo` |
| Entidad (IPRESS / Universidad) | `Combobox` (`components/ui/combobox`) | `ipress`, `universidad`, `solicitante` |
| Ámbito geográfico sanitario | `Select` (catálogo) | `ambito_geografico_sanitario` |
| Granularidad temporal | `Select` (día/mes/año) | agrupación de la serie |

> Falta un componente de calendario/rango: añadir `DateRangePicker` (Popover + Calendar shadcn)
> como tarea de infra de v1.

Reglas UX (skill §10): granularidad de tiempo explícita, filtros en URL, `empty-data-state` y
skeleton de carga por tarjeta, leyenda visible + tooltip, color nunca como único indicador,
export CSV en tablas pesadas (v2).

## 3. Lista de gráficos

`[v1]` = primer spec · `[v2]` = posterior.

### 3.1 Fila de KPIs `[v1]`
Tarjetas `Card` + métrica grande + `Badge` de variación (vs. periodo anterior del rango):
1. **Convenios vigentes** (count `estado=VIGENTE`).
2. **Internados activos** (count internados en curso).
3. **Actividades validadas** (count `estado=VALIDADA`) + % sobre total.
4. **Carga horaria total** (suma `carga_horaria` de actividades en rango).

### 3.2 Convenios
| # | Gráfico | Tipo (Recharts/shadcn) | Dato / eje | Filtros clave |
|---|---------|------------------------|------------|----------------|
| **C1** `[v1]` | Convenios por estado | **BarChart horizontal** | conteo por `estado_codigo` (etapas del flujo) | tipo, rango `fecha_solicitud` |
| **C2** `[v1]` | Marco vs. Específico | **PieChart (donut)** | proporción por `tipo_convenio` (2 cat.) | rango fechas |
| **C3** `[v1]` | Solicitudes en el tiempo | **AreaChart** | serie de `fecha_solicitud` agrupada (día/mes) | tipo, estado |
| C4 `[v2]` | Próximos a vencer | **Bar list** (compuesto) | convenios ordenados por `fecha_fin` cercana | tipo |
| C5 `[v2]` | Top entidades solicitantes | **Bar list** (compuesto) | conteo por `solicitante` (top 10) | tipo, estado |
| C6 `[v2]` | Campos clínicos por especialidad | **BarChart** | suma `cantidad_maxima` por `especialidad` | ámbito geográfico |

### 3.3 Internados
| # | Gráfico | Tipo | Dato / eje | Filtros clave |
|---|---------|------|------------|----------------|
| **I1** `[v1]` | Internados por estado | **BarChart horizontal** | conteo por `estado_codigo` | convenio, ámbito |
| **I2** `[v1]` | Altas de internados en el tiempo | **AreaChart** | serie de `fecha_inicio` (mes) | universidad, ámbito |
| **I5** `[v1]` | Rotaciones por estado | **BarChart** | conteo `rotation-statuses` (SOLICITADA…EN_CURSO) | ipress, servicio_area |
| I3 `[v2]` | Internados por IPRESS (sede) | **Bar list** | conteo por `ipress` (top) | ámbito, rango fechas |
| I4 `[v2]` | Internados por universidad | **PieChart/BarChart** | conteo por `universidad` del interno | rango fechas |
| I6 `[v2]` | Rotaciones por interno (0–4, RN-9) | **BarChart** | distribución de nº de rotaciones | universidad |

### 3.4 Actividades docente-asistenciales
| # | Gráfico | Tipo | Dato / eje | Filtros clave |
|---|---------|------|------------|----------------|
| **A1** `[v1]` | Actividades por estado | **PieChart (donut)** | proporción `estado_codigo` (REGISTRADA/VALIDADA/OBSERVADA…) | tipo, tutor |
| **A2** `[v1]` | Actividades en el tiempo | **AreaChart** (multi-serie por estado) | serie de `fecha_actividad` (semana/mes) | tipo, ipress |
| **A3** `[v1]` | Carga horaria por tipo de actividad | **BarChart** | suma `carga_horaria` por `tipo_actividad` | rango fechas, ipress |
| A4 `[v2]` | Carga horaria por servicio/área | **Bar list** | suma `carga_horaria` por `servicio_area` | ipress |
| A5 `[v2]` | Tasa de validación por tutor | **BarChart** | % `VALIDADA` sobre total por `tutor` | rango fechas |
| A6 `[v2]` | Embudo de validación | **BarChart horizontal** (proxy funnel) | REGISTRADA→VALIDADA/OBSERVADA→SUBSANADA | tipo |

> Recharts no trae *funnel* nativo: A6 y los flujos de estado (C1/I1) se modelan como **BarChart
> horizontal ordenado** por etapa del flujo — legible y accesible.

## 4. Orden de implementación — v1

1. **Infra:** dependencia `recharts` + `components/ui/chart.tsx` (shadcn) · `DateRangePicker`
   (Popover + Calendar) · barra de filtros global sincronizada a la URL · helpers de agregación
   en cliente (group-by estado / fecha / tipo) con TanStack Query (`select`).
2. **KPIs** (3.1) — las 4 tarjetas.
3. **Convenios** — C1, C2, C3.
4. **Internados** — I1, I2, I5.
5. **Actividades** — A1, A2, A3.
6. En paralelo: registrar requerimiento de endpoints `/stats/` (vía B) al equipo backend.

## 5. Checklist de calidad por gráfico (ui-ux-pro-max §10)

- [ ] Tipo acorde al dato (tendencia→área/línea, comparación→barra, proporción→donut ≤5 cat.).
- [ ] Leyenda visible + tooltip con valor exacto en hover/tap.
- [ ] Skeleton de carga y estado vacío ("Sin datos" + guía); nunca eje en blanco.
- [ ] Estado de error con acción de reintento.
- [ ] Colores accesibles (no solo color: etiqueta/patrón); contraste datos ≥3:1.
- [ ] Números con formato local (es-PE); fechas con granularidad rotulada.
- [ ] Responsive: en móvil reduce ticks / barras horizontales; sin scroll horizontal.
- [ ] `prefers-reduced-motion` respetado en animaciones de entrada.
