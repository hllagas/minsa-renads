"use client";

import { useMemo } from "react";

import type { DashboardFilters } from "@/lib/dashboard/types";
import {
  sortByFlow,
  useInternadosEnTiempo,
  useInternadosPorEstado,
  useRotacionesPorEstado,
} from "@/lib/dashboard/hooks";
import { useCatalogLabels } from "@/lib/dashboard/catalogs";
import { ChartCard } from "@/components/dashboard/chart-card";
import { CategoryBarChart } from "@/components/dashboard/charts/category-bar-chart";
import { TimeAreaChart } from "@/components/dashboard/charts/time-area-chart";

export function InternadosSection({ filters }: { filters: DashboardFilters }) {
  const internshipStatuses = useCatalogLabels("internship-statuses");
  const rotationStatuses = useCatalogLabels("rotation-statuses");

  const porEstado = useInternadosPorEstado(filters);
  const enTiempo = useInternadosEnTiempo(filters);
  const rotaciones = useRotacionesPorEstado(filters);

  const estadoData = useMemo(
    () =>
      sortByFlow(porEstado.data ?? [], internshipStatuses.order).map((b) => ({
        label: internshipStatuses.label(b.key),
        value: b.count,
      })),
    [porEstado.data, internshipStatuses],
  );

  const rotacionData = useMemo(
    () =>
      sortByFlow(rotaciones.data ?? [], rotationStatuses.order).map((b) => ({
        label: rotationStatuses.label(b.key),
        value: b.count,
      })),
    [rotaciones.data, rotationStatuses],
  );

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <ChartCard
        title="Internados por estado"
        description="Conteo por estado del internado (rango de fecha de inicio)."
        isLoading={porEstado.isLoading}
        isError={porEstado.isError}
        isEmpty={estadoData.length === 0}
        truncated={porEstado.truncated}
        onRetry={porEstado.refetch}
      >
        <CategoryBarChart data={estadoData} orientation="horizontal" valueLabel="Internados" />
      </ChartCard>

      <ChartCard
        title="Rotaciones por estado"
        description="Conteo de rotaciones por estado."
        isLoading={rotaciones.isLoading}
        isError={rotaciones.isError}
        isEmpty={rotacionData.length === 0}
        truncated={rotaciones.truncated}
        onRetry={rotaciones.refetch}
      >
        <CategoryBarChart data={rotacionData} orientation="vertical" valueLabel="Rotaciones" />
      </ChartCard>

      <ChartCard
        title="Altas de internados en el tiempo"
        description="Internados iniciados por periodo."
        isLoading={enTiempo.isLoading}
        isError={enTiempo.isError}
        isEmpty={(enTiempo.data ?? []).length === 0}
        truncated={enTiempo.truncated}
        onRetry={enTiempo.refetch}
        className="lg:col-span-2"
      >
        <TimeAreaChart
          data={enTiempo.data ?? []}
          valueLabel="Internados"
          granularidad={filters.granularidad}
        />
      </ChartCard>
    </div>
  );
}
