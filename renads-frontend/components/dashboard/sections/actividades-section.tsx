"use client";

import { useCallback, useMemo } from "react";

import type { DashboardFilters } from "@/lib/dashboard/types";
import {
  useActividadesCargaPorTipo,
  useActividadesEnTiempo,
  useActividadesPorEstado,
} from "@/lib/dashboard/hooks";
import { topNWithOther } from "@/lib/dashboard/aggregation";
import { useCatalogLabels } from "@/lib/dashboard/catalogs";
import { ChartCard } from "@/components/dashboard/chart-card";
import { CategoryBarChart } from "@/components/dashboard/charts/category-bar-chart";
import { DonutChart } from "@/components/dashboard/charts/donut-chart";
import { StackedAreaChart } from "@/components/dashboard/charts/stacked-area-chart";

const horasFormatter = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 });

export function ActividadesSection({ filters }: { filters: DashboardFilters }) {
  const statuses = useCatalogLabels("activity-statuses");

  const porEstado = useActividadesPorEstado(filters);
  const enTiempo = useActividadesEnTiempo(filters);
  const cargaPorTipo = useActividadesCargaPorTipo(filters);

  // A1: máx. 5 categorías + "Otros" para mantener legible el donut.
  const estadoData = useMemo(
    () =>
      topNWithOther(porEstado.data ?? [], 5).map((b) => ({
        key: b.key,
        label: b.key === "Otros" ? "Otros" : statuses.label(b.key),
        value: b.count,
      })),
    [porEstado.data, statuses],
  );

  const cargaData = useMemo(
    () =>
      (cargaPorTipo.data ?? []).map((b) => ({ label: b.key, value: b.total })),
    [cargaPorTipo.data],
  );

  const labelEstado = useCallback((code: string) => statuses.label(code), [statuses]);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard
        title="Actividades por estado"
        description="Proporción de actividades por estado (rango de fecha de actividad)."
        isLoading={porEstado.isLoading}
        isError={porEstado.isError}
        isEmpty={estadoData.length === 0}
        truncated={porEstado.truncated}
        onRetry={porEstado.refetch}
      >
        <DonutChart data={estadoData} totalLabel="Actividades" />
      </ChartCard>

      <ChartCard
        title="Carga horaria por tipo"
        description="Suma de carga horaria por tipo de actividad."
        isLoading={cargaPorTipo.isLoading}
        isError={cargaPorTipo.isError}
        isEmpty={cargaData.length === 0}
        truncated={cargaPorTipo.truncated}
        onRetry={cargaPorTipo.refetch}
      >
        <CategoryBarChart
          data={cargaData}
          orientation="vertical"
          valueLabel="Horas"
          valueFormatter={(v) => `${horasFormatter.format(v)} h`}
        />
      </ChartCard>

      <ChartCard
        title="Actividades en el tiempo"
        description="Actividades por periodo, desglosadas por estado."
        isLoading={enTiempo.isLoading}
        isError={enTiempo.isError}
        isEmpty={(enTiempo.data?.rows ?? []).length === 0}
        truncated={enTiempo.truncated}
        onRetry={enTiempo.refetch}
        className="lg:col-span-2"
      >
        <StackedAreaChart
          series={enTiempo.data ?? { buckets: [], groups: [], rows: [] }}
          granularidad={filters.granularidad}
          labelFor={labelEstado}
        />
      </ChartCard>
    </div>
  );
}
