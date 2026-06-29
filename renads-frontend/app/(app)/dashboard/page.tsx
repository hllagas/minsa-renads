"use client";

import { PageHeader } from "@/components/data/page-header";
import { useDashboardFilters } from "@/lib/dashboard/use-dashboard-filters";
import { DashboardFilters } from "@/components/dashboard/dashboard-filters";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { ConveniosSection } from "@/components/dashboard/sections/convenios-section";
import { InternadosSection } from "@/components/dashboard/sections/internados-section";
import { ActividadesSection } from "@/components/dashboard/sections/actividades-section";

/**
 * Pantalla única del dashboard: barra de filtros transversal (sincronizada a la URL), fila de KPIs y
 * la sección del módulo activo (Convenios / Internados / Actividades). Vía A: agregación en cliente.
 */
export default function DashboardPage() {
  const { filters } = useDashboardFilters();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Indicadores y gráficos estadísticos de RENADS."
      />

      <DashboardFilters />

      <KpiCards filters={filters} />

      {filters.modulo === "convenios" ? <ConveniosSection filters={filters} /> : null}
      {filters.modulo === "internados" ? <InternadosSection filters={filters} /> : null}
      {filters.modulo === "actividades" ? <ActividadesSection filters={filters} /> : null}
    </div>
  );
}
