"use client";

import { useMemo } from "react";

import type { DashboardFilters } from "@/lib/dashboard/types";
import {
  sortByFlow,
  useConveniosEnTiempo,
  useConveniosPorEstado,
  useConveniosPorTipo,
} from "@/lib/dashboard/hooks";
import { useCatalogLabels } from "@/lib/dashboard/catalogs";
import { ChartCard } from "@/components/dashboard/chart-card";
import { CategoryBarChart } from "@/components/dashboard/charts/category-bar-chart";
import { DonutChart } from "@/components/dashboard/charts/donut-chart";
import { TimeAreaChart } from "@/components/dashboard/charts/time-area-chart";

export function ConveniosSection({ filters }: { filters: DashboardFilters }) {
  const statuses = useCatalogLabels("convention-statuses");
  const porEstado = useConveniosPorEstado(filters);
  const porTipo = useConveniosPorTipo(filters);
  const enTiempo = useConveniosEnTiempo(filters);

  const estadoData = useMemo(
    () =>
      sortByFlow(porEstado.data ?? [], statuses.order).map((b) => ({
        label: statuses.label(b.key),
        value: b.count,
      })),
    [porEstado.data, statuses],
  );

  const tipoData = useMemo(
    () => (porTipo.data ?? []).map((b) => ({ key: b.key, label: b.key, value: b.count })),
    [porTipo.data],
  );

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard
        title="Convenios por estado"
        description="Conteo por etapa del flujo (rango de fecha de solicitud)."
        isLoading={porEstado.isLoading}
        isError={porEstado.isError}
        isEmpty={estadoData.length === 0}
        truncated={porEstado.truncated}
        onRetry={porEstado.refetch}
      >
        <CategoryBarChart data={estadoData} orientation="horizontal" valueLabel="Convenios" />
      </ChartCard>

      <ChartCard
        title="Marco vs. Específico"
        description="Proporción de convenios por tipo."
        isLoading={porTipo.isLoading}
        isError={porTipo.isError}
        isEmpty={tipoData.length === 0}
        truncated={porTipo.truncated}
        onRetry={porTipo.refetch}
      >
        <DonutChart data={tipoData} totalLabel="Convenios" />
      </ChartCard>

      <ChartCard
        title="Solicitudes en el tiempo"
        description="Convenios solicitados por periodo."
        isLoading={enTiempo.isLoading}
        isError={enTiempo.isError}
        isEmpty={(enTiempo.data ?? []).length === 0}
        truncated={enTiempo.truncated}
        onRetry={enTiempo.refetch}
        className="lg:col-span-2"
      >
        <TimeAreaChart
          data={enTiempo.data ?? []}
          valueLabel="Solicitudes"
          granularidad={filters.granularidad}
        />
      </ChartCard>
    </div>
  );
}
