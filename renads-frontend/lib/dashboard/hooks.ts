"use client";

import { useCallback } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";

import type { ListParams } from "@/lib/api/query";
import { fetchAllPages, type FetchAllResult } from "@/lib/dashboard/fetch-all";
import {
  countBy,
  isWithinRange,
  previousRange,
  sumBy,
  timeSeries,
  timeSeriesByGroup,
} from "@/lib/dashboard/aggregation";
import type {
  CountBucket,
  DashboardFilters,
  KpiCard,
  KpiDelta,
  SumBucket,
  TimeBucket,
  TimeSeriesGroup,
} from "@/lib/dashboard/types";
import type { ConventionRead } from "@/lib/convenios/hooks";
import type { InternshipRead, RotationRead } from "@/lib/internados/hooks";
import type { TeachingActivityRead } from "@/lib/actividades/hooks";

type ApiParams = ListParams["filters"];

/** Resultado uniforme de un hook de gráfico (datos agregados + estados de carga). */
export interface ChartData<D> {
  data: D | undefined;
  truncated: boolean;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

const RAW_STALE = 60_000;

function rawQueryKey(endpoint: string, apiParams: ApiParams) {
  return ["dashboard", "raw", endpoint, apiParams ?? {}] as const;
}

/**
 * Hook base de la Vía A: trae todas las filas del endpoint (con los filtros del servidor) y aplica
 * una agregación memoizada en `select`. Varios gráficos con los mismos `apiParams` comparten una
 * sola petición (misma `queryKey`) y cada uno aplica su propio `select`.
 */
function useAggregated<T, D>(
  endpoint: string,
  apiParams: ApiParams,
  aggregate: (items: T[]) => D,
): ChartData<D> {
  const select = useCallback(
    (res: FetchAllResult<T>) => ({
      data: aggregate(res.results),
      truncated: res.truncated,
    }),
    [aggregate],
  );

  const query = useQuery({
    queryKey: rawQueryKey(endpoint, apiParams),
    queryFn: () => fetchAllPages<T>(endpoint, apiParams),
    staleTime: RAW_STALE,
    select,
  });

  return {
    data: query.data?.data,
    truncated: query.data?.truncated ?? false,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: () => void query.refetch(),
  };
}

/** Parse de `carga_horaria` (decimal serializado como string|null) a número. */
function parseCargaHoraria(value: string | null | undefined): number {
  if (value == null) return 0;
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

/** Ordena buckets de conteo por el orden de flujo del catálogo (luego alfabético). */
export function sortByFlow(
  buckets: CountBucket[],
  order: (codigo: string) => number,
): CountBucket[] {
  return [...buckets].sort((a, b) => {
    const oa = order(a.key);
    const ob = order(b.key);
    if (oa !== ob) return oa - ob;
    return a.key.localeCompare(b.key);
  });
}

// === Convenios (endpoint `conventions`, fecha = fecha_solicitud) ============

function convenioApiParams(filters: DashboardFilters): ApiParams {
  return { tipo_convenio: filters.tipo };
}

/** C1 — Convenios por estado (`estado_codigo`) dentro del rango de `fecha_solicitud`. */
export function useConveniosPorEstado(filters: DashboardFilters): ChartData<CountBucket[]> {
  const { desde, hasta } = filters;
  const aggregate = useCallback(
    (items: ConventionRead[]) =>
      countBy(
        items.filter((c) => isWithinRange(c.fecha_solicitud, desde, hasta)),
        (c) => c.estado_codigo,
      ),
    [desde, hasta],
  );
  return useAggregated<ConventionRead, CountBucket[]>(
    "conventions",
    convenioApiParams(filters),
    aggregate,
  );
}

/** C2 — Marco vs. Específico: proporción por `tipo_convenio` (etiqueta legible del read). */
export function useConveniosPorTipo(filters: DashboardFilters): ChartData<CountBucket[]> {
  const { desde, hasta } = filters;
  const aggregate = useCallback(
    (items: ConventionRead[]) =>
      countBy(
        items.filter((c) => isWithinRange(c.fecha_solicitud, desde, hasta)),
        (c) => c.tipo_convenio,
      ),
    [desde, hasta],
  );
  return useAggregated<ConventionRead, CountBucket[]>(
    "conventions",
    convenioApiParams(filters),
    aggregate,
  );
}

/** C3 — Solicitudes en el tiempo: serie de `fecha_solicitud` por granularidad activa. */
export function useConveniosEnTiempo(filters: DashboardFilters): ChartData<TimeBucket[]> {
  const { desde, hasta, granularidad } = filters;
  const aggregate = useCallback(
    (items: ConventionRead[]) =>
      timeSeries(
        items.filter((c) => isWithinRange(c.fecha_solicitud, desde, hasta)),
        (c) => c.fecha_solicitud,
        granularidad,
      ),
    [desde, hasta, granularidad],
  );
  return useAggregated<ConventionRead, TimeBucket[]>(
    "conventions",
    convenioApiParams(filters),
    aggregate,
  );
}

// === Internados (endpoint `internships`, fecha = fecha_inicio) ==============

function internadoApiParams(filters: DashboardFilters): ApiParams {
  return {
    ambito_geografico_sanitario: filters.ambito,
    ipress: filters.entidad,
  };
}

/** I1 — Internados por estado (`estado_codigo`) dentro del rango de `fecha_inicio`. */
export function useInternadosPorEstado(filters: DashboardFilters): ChartData<CountBucket[]> {
  const { desde, hasta } = filters;
  const aggregate = useCallback(
    (items: InternshipRead[]) =>
      countBy(
        items.filter((i) => isWithinRange(i.fecha_inicio, desde, hasta)),
        (i) => i.estado_codigo,
      ),
    [desde, hasta],
  );
  return useAggregated<InternshipRead, CountBucket[]>(
    "internships",
    internadoApiParams(filters),
    aggregate,
  );
}

/** I2 — Altas de internados en el tiempo: serie de `fecha_inicio` por granularidad activa. */
export function useInternadosEnTiempo(filters: DashboardFilters): ChartData<TimeBucket[]> {
  const { desde, hasta, granularidad } = filters;
  const aggregate = useCallback(
    (items: InternshipRead[]) =>
      timeSeries(
        items.filter((i) => isWithinRange(i.fecha_inicio, desde, hasta)),
        (i) => i.fecha_inicio,
        granularidad,
      ),
    [desde, hasta, granularidad],
  );
  return useAggregated<InternshipRead, TimeBucket[]>(
    "internships",
    internadoApiParams(filters),
    aggregate,
  );
}

/** I5 — Rotaciones por estado (`estado_codigo`) dentro del rango de `fecha_inicio`. */
export function useRotacionesPorEstado(filters: DashboardFilters): ChartData<CountBucket[]> {
  const { desde, hasta, entidad } = filters;
  // TODO(contrato): `rotations` filtra por `ipress_origen`/`ipress_destino` (no `ipress`).
  // Mapeamos la entidad global al origen de la rotación, que es el supuesto más conservador.
  const apiParams: ApiParams = { ipress_origen: entidad };
  const aggregate = useCallback(
    (items: RotationRead[]) =>
      countBy(
        items.filter((r) => isWithinRange(r.fecha_inicio, desde, hasta)),
        (r) => r.estado_codigo,
      ),
    [desde, hasta],
  );
  return useAggregated<RotationRead, CountBucket[]>("rotations", apiParams, aggregate);
}

// === Actividades (endpoint `teaching-activities`, fecha = fecha_actividad) ==

function actividadApiParams(filters: DashboardFilters): ApiParams {
  return { tipo_actividad: filters.tipo, ipress: filters.entidad };
}

/** A1 — Actividades por estado (`estado_codigo`) dentro del rango de `fecha_actividad`. */
export function useActividadesPorEstado(
  filters: DashboardFilters,
): ChartData<CountBucket[]> {
  const { desde, hasta } = filters;
  const aggregate = useCallback(
    (items: TeachingActivityRead[]) =>
      countBy(
        items.filter((a) => isWithinRange(a.fecha_actividad, desde, hasta)),
        (a) => a.estado_codigo,
      ),
    [desde, hasta],
  );
  return useAggregated<TeachingActivityRead, CountBucket[]>(
    "teaching-activities",
    actividadApiParams(filters),
    aggregate,
  );
}

/** A2 — Actividades en el tiempo, multi-serie por `estado_codigo`. */
export function useActividadesEnTiempo(
  filters: DashboardFilters,
): ChartData<TimeSeriesGroup> {
  const { desde, hasta, granularidad } = filters;
  const aggregate = useCallback(
    (items: TeachingActivityRead[]) =>
      timeSeriesByGroup(
        items.filter((a) => isWithinRange(a.fecha_actividad, desde, hasta)),
        (a) => a.fecha_actividad,
        (a) => a.estado_codigo,
        granularidad,
      ),
    [desde, hasta, granularidad],
  );
  return useAggregated<TeachingActivityRead, TimeSeriesGroup>(
    "teaching-activities",
    actividadApiParams(filters),
    aggregate,
  );
}

/** A3 — Carga horaria por tipo de actividad (suma de `carga_horaria`). */
export function useActividadesCargaPorTipo(
  filters: DashboardFilters,
): ChartData<SumBucket[]> {
  const { desde, hasta } = filters;
  const aggregate = useCallback(
    (items: TeachingActivityRead[]) =>
      sumBy(
        items.filter((a) => isWithinRange(a.fecha_actividad, desde, hasta)),
        (a) => a.tipo_actividad,
        (a) => parseCargaHoraria(a.carga_horaria),
      ),
    [desde, hasta],
  );
  return useAggregated<TeachingActivityRead, SumBucket[]>(
    "teaching-activities",
    actividadApiParams(filters),
    aggregate,
  );
}

// === KPIs ===================================================================

interface StatusCatalogItem {
  id: number;
  codigo?: string;
  nombre?: string;
}

/** Calcula la variación porcentual entre el periodo actual y el anterior. */
function computeDelta(current: number, previous: number | null): KpiDelta | null {
  if (previous == null) return null;
  if (previous === 0) {
    return { porcentaje: current > 0 ? 100 : 0, direccion: current > 0 ? "up" : "flat" };
  }
  const pct = ((current - previous) / previous) * 100;
  return {
    porcentaje: pct,
    direccion: pct > 0.0001 ? "up" : pct < -0.0001 ? "down" : "flat",
  };
}

const integerFormatter = new Intl.NumberFormat("es-PE");
const decimalFormatter = new Intl.NumberFormat("es-PE", {
  maximumFractionDigits: 1,
});

/**
 * KPIs del dashboard (Vía A). Calcula las 4 métricas en el rango activo y su variación respecto al
 * periodo anterior equivalente. Los KPIs son transversales: ignoran los filtros de módulo
 * (tipo/entidad/ámbito) y solo consideran el rango de fechas.
 */
export function useKpis(filters: DashboardFilters): {
  cards: KpiCard[];
  isLoading: boolean;
  isError: boolean;
  truncated: boolean;
  refetch: () => void;
} {
  const { desde, hasta } = filters;
  const prev = previousRange(desde, hasta);

  const results = useQueries({
    queries: [
      {
        queryKey: rawQueryKey("conventions", {}),
        queryFn: () => fetchAllPages<ConventionRead>("conventions", {}),
        staleTime: RAW_STALE,
      },
      {
        queryKey: rawQueryKey("internships", {}),
        queryFn: () => fetchAllPages<InternshipRead>("internships", {}),
        staleTime: RAW_STALE,
      },
      {
        queryKey: rawQueryKey("teaching-activities", {}),
        queryFn: () => fetchAllPages<TeachingActivityRead>("teaching-activities", {}),
        staleTime: RAW_STALE,
      },
    ],
  });

  const statusQuery = useQuery({
    queryKey: ["dashboard", "catalog", "internship-statuses"],
    queryFn: () => fetchAllPages<StatusCatalogItem>("internship-statuses"),
    staleTime: 10 * 60_000,
  });

  const [convQ, interQ, actsQ] = results;
  const conventions = convQ.data?.results ?? [];
  const internships = interQ.data?.results ?? [];
  const activities = actsQ.data?.results ?? [];

  // TODO(contrato): el código exacto de "internado activo/en curso" no está fijado. Se deriva del
  // catálogo `internship-statuses` buscando códigos que representen actividad (CURSO/ACTIV), sin
  // hardcodear nombres. Confirmar con backend el código real.
  const activeCodes = new Set(
    (statusQuery.data?.results ?? [])
      .map((s) => s.codigo ?? "")
      .filter((code) => /CURSO|ACTIV/i.test(code)),
  );

  const inCurrent = (date: string | null | undefined) =>
    isWithinRange(date, desde, hasta);
  const inPrev = (date: string | null | undefined) =>
    prev ? isWithinRange(date, prev.desde, prev.hasta) : false;

  // 1. Convenios vigentes (estado VIGENTE) por fecha_solicitud.
  const vigentesCur = conventions.filter(
    (c) => c.estado_codigo === "VIGENTE" && inCurrent(c.fecha_solicitud),
  ).length;
  const vigentesPrev = prev
    ? conventions.filter(
        (c) => c.estado_codigo === "VIGENTE" && inPrev(c.fecha_solicitud),
      ).length
    : null;

  // 2. Internados activos (estado en activeCodes) por fecha_inicio.
  const activosCur = internships.filter(
    (i) => activeCodes.has(i.estado_codigo) && inCurrent(i.fecha_inicio),
  ).length;
  const activosPrev = prev
    ? internships.filter(
        (i) => activeCodes.has(i.estado_codigo) && inPrev(i.fecha_inicio),
      ).length
    : null;

  // 3. Actividades validadas (estado VALIDADA) + % sobre el total, por fecha_actividad.
  const actsCur = activities.filter((a) => inCurrent(a.fecha_actividad));
  const validadasCur = actsCur.filter((a) => a.estado_codigo === "VALIDADA").length;
  const validadasPrev = prev
    ? activities.filter(
        (a) => a.estado_codigo === "VALIDADA" && inPrev(a.fecha_actividad),
      ).length
    : null;
  const pctValidadas = actsCur.length > 0 ? (validadasCur / actsCur.length) * 100 : 0;

  // 4. Carga horaria total (suma carga_horaria) por fecha_actividad.
  const cargaCur = actsCur.reduce((acc, a) => acc + parseCargaHoraria(a.carga_horaria), 0);
  const cargaPrev = prev
    ? activities
        .filter((a) => inPrev(a.fecha_actividad))
        .reduce((acc, a) => acc + parseCargaHoraria(a.carga_horaria), 0)
    : null;

  const cards: KpiCard[] = [
    {
      id: "convenios-vigentes",
      titulo: "Convenios vigentes",
      valor: integerFormatter.format(vigentesCur),
      delta: computeDelta(vigentesCur, vigentesPrev),
    },
    {
      id: "internados-activos",
      titulo: "Internados activos",
      valor: integerFormatter.format(activosCur),
      delta: computeDelta(activosCur, activosPrev),
    },
    {
      id: "actividades-validadas",
      titulo: "Actividades validadas",
      valor: integerFormatter.format(validadasCur),
      detalle: `${decimalFormatter.format(pctValidadas)} % del total`,
      delta: computeDelta(validadasCur, validadasPrev),
    },
    {
      id: "carga-horaria-total",
      titulo: "Carga horaria total",
      valor: `${decimalFormatter.format(cargaCur)} h`,
      delta: computeDelta(cargaCur, cargaPrev),
    },
  ];

  return {
    cards,
    isLoading: results.some((q) => q.isLoading) || statusQuery.isLoading,
    isError: results.some((q) => q.isError),
    truncated: results.some((q) => q.data?.truncated ?? false),
    refetch: () => {
      results.forEach((q) => void q.refetch());
      void statusQuery.refetch();
    },
  };
}
