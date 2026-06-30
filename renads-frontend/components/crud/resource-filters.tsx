"use client";

import type { FilterConfig } from "@/lib/crud/types";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Valores de filtros activos (todos como string; vacío = sin filtrar). */
export type FilterValues = Record<string, string>;

/** Sentinela para la opción «Todos» (base-ui Select no admite value vacío). */
const ALL = "__all__";

/**
 * Barra de filtros declarativos para un listado DRF. Cada filtro alimenta `ListParams.filters`.
 * Soporta select FK (`EntityCombobox`), select de enum (`choices`), boolean (Sí/No) y texto.
 */
export function ResourceFilters({
  filters,
  values,
  onChange,
  onClear,
}: {
  filters: FilterConfig[];
  values: FilterValues;
  onChange: (name: string, value: string) => void;
  onClear: () => void;
}) {
  const hasActive = Object.values(values).some((v) => v !== "");

  return (
    <div className="mb-4 flex flex-wrap items-end gap-3">
      {filters.map((filter) => (
        <div key={filter.name} className="grid gap-1.5">
          <Label className="text-xs text-muted-foreground">{filter.label}</Label>
          {filter.type === "text" ? (
            <Input
              value={values[filter.name] ?? ""}
              placeholder={filter.placeholder ?? "Filtrar…"}
              onChange={(e) => onChange(filter.name, e.target.value)}
              className="h-8 w-full sm:w-44"
            />
          ) : filter.type === "boolean" ? (
            <Select
              items={[
                { value: ALL, label: "Todos" },
                { value: "true", label: "Sí" },
                { value: "false", label: "No" },
              ]}
              value={values[filter.name] || ALL}
              onValueChange={(v: string | null) =>
                onChange(filter.name, v === ALL || v === null ? "" : v)
              }
            >
              <SelectTrigger size="sm" className="w-36">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Todos</SelectItem>
                <SelectItem value="true">Sí</SelectItem>
                <SelectItem value="false">No</SelectItem>
              </SelectContent>
            </Select>
          ) : filter.choices ? (
            <Select
              items={[
                { value: ALL, label: "Todos" },
                ...filter.choices.map((c) => ({ value: c.value, label: c.label })),
              ]}
              value={values[filter.name] || ALL}
              onValueChange={(v: string | null) =>
                onChange(filter.name, v === ALL || v === null ? "" : v)
              }
            >
              <SelectTrigger size="sm" className="w-48">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Todos</SelectItem>
                {filter.choices.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <div className="w-full sm:w-56">
              <EntityCombobox
                endpoint={filter.optionsEndpoint!}
                params={filter.optionsParams}
                toLabel={filter.optionsToLabel}
                value={values[filter.name] ? Number(values[filter.name]) : null}
                onChange={(val) => onChange(filter.name, val != null ? String(val) : "")}
                placeholder="Todos"
              />
            </div>
          )}
        </div>
      ))}
      {hasActive ? (
        <Button variant="ghost" size="sm" onClick={onClear} className="h-8">
          Limpiar filtros
        </Button>
      ) : null}
    </div>
  );
}
