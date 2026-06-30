"use client";

import { useEffect, useMemo } from "react";

import { useAuthStore, userHasRole } from "@/lib/auth/store";
import type {
  DashboardFilters as Filters,
  DashboardModule,
  Granularity,
} from "@/lib/dashboard/types";
import { useDashboardFilters } from "@/lib/dashboard/use-dashboard-filters";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { DateRangePicker } from "@/components/dashboard/date-range-picker";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Roles por módulo (alineados con `AppShell.NAV_ITEMS`; gating de UX, no de seguridad). */
const MODULE_ROLES: Record<DashboardModule, string[]> = {
  convenios: ["Administrador RENADS", "DIGEP", "CONAPRES", "OGAJ", "Secretaría General"],
  internados: ["Administrador RENADS", "Universidad", "Autoridad de convenio"],
  actividades: ["Administrador RENADS", "Universidad", "Tutor", "Sede docente"],
};

const MODULE_LABELS: Record<DashboardModule, string> = {
  convenios: "Convenios",
  internados: "Internados",
  actividades: "Actividades",
};

export function DashboardFilters() {
  const { filters, setFilters } = useDashboardFilters();
  const user = useAuthStore((s) => s.user);

  const visibleModules = useMemo<DashboardModule[]>(() => {
    const modules = (Object.keys(MODULE_ROLES) as DashboardModule[]).filter((m) =>
      userHasRole(user, ...MODULE_ROLES[m]),
    );
    // Si el usuario no coincide con ningún rol de módulo, mostrar todos (evita un dashboard vacío).
    return modules.length > 0 ? modules : (Object.keys(MODULE_ROLES) as DashboardModule[]);
  }, [user]);

  // Si el módulo activo (de la URL) no es visible para el usuario, conmuta al primero visible.
  useEffect(() => {
    if (!visibleModules.includes(filters.modulo)) {
      setFilters({ modulo: visibleModules[0] });
    }
  }, [visibleModules, filters.modulo, setFilters]);

  const onModuleChange = (value: string) => {
    // Al cambiar de módulo se limpian los filtros dependientes del módulo.
    setFilters({
      modulo: value as DashboardModule,
      tipo: null,
      entidad: null,
      ambito: null,
    });
  };

  return (
    <div className="space-y-4">
      <Tabs value={filters.modulo} onValueChange={(v) => onModuleChange(String(v))}>
        <TabsList>
          {visibleModules.map((m) => (
            <TabsTrigger key={m} value={m}>
              {MODULE_LABELS[m]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <Label className="text-xs text-muted-foreground">Rango de fechas</Label>
          <DateRangePicker
            value={{ desde: filters.desde, hasta: filters.hasta }}
            onChange={(r) => setFilters({ desde: r.desde, hasta: r.hasta })}
          />
        </div>

        <ModuleEntityFilters filters={filters} setFilters={setFilters} />

        <div className="grid gap-1.5">
          <Label className="text-xs text-muted-foreground">Granularidad</Label>
          <Select
            items={[
              { value: "dia", label: "Día" },
              { value: "mes", label: "Mes" },
              { value: "anio", label: "Año" },
            ]}
            value={filters.granularidad}
            onValueChange={(v) => setFilters({ granularidad: v as Granularity })}
          >
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Granularidad" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dia">Día</SelectItem>
              <SelectItem value="mes">Mes</SelectItem>
              <SelectItem value="anio">Año</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}

/** Filtros de tipo/entidad/ámbito, mostrados según el módulo activo (mapeo a filtros del backend). */
function ModuleEntityFilters({
  filters,
  setFilters,
}: {
  filters: Filters;
  setFilters: (patch: Partial<Filters>) => void;
}) {
  const { modulo } = filters;

  return (
    <>
      {(modulo === "convenios" || modulo === "actividades") && (
        <div className="grid gap-1.5">
          <Label className="text-xs text-muted-foreground">Tipo</Label>
          <div className="w-56">
            <EntityCombobox
              endpoint={modulo === "convenios" ? "convention-types" : "activity-types"}
              value={filters.tipo}
              onChange={(v) => setFilters({ tipo: v })}
              placeholder="Todos los tipos"
            />
          </div>
        </div>
      )}

      {(modulo === "internados" || modulo === "actividades") && (
        <div className="grid gap-1.5">
          <Label className="text-xs text-muted-foreground">IPRESS</Label>
          <div className="w-56">
            <EntityCombobox
              endpoint="ipress"
              value={filters.entidad}
              onChange={(v) => setFilters({ entidad: v })}
              placeholder="Todas las IPRESS"
            />
          </div>
        </div>
      )}

      {modulo === "internados" && (
        <div className="grid gap-1.5">
          <Label className="text-xs text-muted-foreground">Ámbito geográfico</Label>
          <div className="w-56">
            <EntityCombobox
              endpoint="health-geographic-scopes"
              value={filters.ambito}
              onChange={(v) => setFilters({ ambito: v })}
              placeholder="Todos los ámbitos"
            />
          </div>
        </div>
      )}
    </>
  );
}
