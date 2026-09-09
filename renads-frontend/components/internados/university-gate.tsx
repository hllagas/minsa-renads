"use client";

import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { useUniversityScope } from "@/lib/auth/scope";
import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Paso «elegir universidad» acotado al alcance del usuario (compartido por Estudiantes, Tutores e
 * Internos). Una universidad autorizada → auto-fija; varias → Select de esas; sin alcance (Admin) →
 * búsqueda sobre todas. El backend es la autoridad final del alcance.
 */
export function useUniversityGate(stepLabel = "Universidad"): {
  universidad: number | null;
  gateUI: ReactNode;
} {
  const { ids, singleId, scoped } = useUniversityScope();
  const [picked, setPicked] = useState<number | null>(singleId);
  const universidad = singleId ?? picked;

  const gateUI = (
    <div className="grid gap-1.5 max-w-md">
      <Label className="flex items-center gap-2 text-sm font-medium">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">
          1
        </span>
        {stepLabel}
      </Label>
      {singleId != null ? (
        <p className="text-sm text-muted-foreground">Acotado a tu universidad autorizada.</p>
      ) : scoped ? (
        <ScopedUniversitySelect ids={ids} value={picked} onChange={setPicked} />
      ) : (
        <EntityCombobox
          endpoint="universities"
          value={picked}
          onChange={setPicked}
          toLabel={(r) => String(r.nombre ?? r.siglas ?? r.id)}
          placeholder="Buscar universidad…"
        />
      )}
    </div>
  );

  return { universidad, gateUI };
}

/** Selector de universidad acotado a los ids autorizados del usuario (alcance múltiple). */
function ScopedUniversitySelect({
  ids,
  value,
  onChange,
}: {
  ids: number[];
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const query = useQuery({
    queryKey: ["universities", "scoped", ids],
    queryFn: () =>
      api.get<Paginated<WithId>>("/universities/").then((r) => r.data.results),
    staleTime: 10 * 60_000,
  });
  const opciones = (query.data ?? []).filter((u) => ids.includes(Number(u.id)));

  return (
    <Select
      value={value != null ? String(value) : ""}
      onValueChange={(v) => onChange(v ? Number(v) : null)}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Selecciona una universidad…" />
      </SelectTrigger>
      <SelectContent>
        {opciones.map((u) => (
          <SelectItem key={u.id} value={String(u.id)}>
            {String(u.nombre ?? u.siglas ?? u.id)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
