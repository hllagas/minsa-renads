"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import type {
  DashboardFilters,
  DashboardModule,
  Granularity,
} from "@/lib/dashboard/types";

const MODULES: DashboardModule[] = ["convenios", "internados", "actividades"];
const GRANULARITIES: Granularity[] = ["dia", "mes", "anio"];

/** Lee un id numérico del querystring (o `null` si ausente/no válido). */
function readNumber(value: string | null): number | null {
  if (!value) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Hook de filtros globales del dashboard sincronizados con la URL (deep-linking). */
export function useDashboardFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo<DashboardFilters>(() => {
    const modulo = searchParams.get("modulo");
    const granularidad = searchParams.get("gran");
    return {
      desde: searchParams.get("desde"),
      hasta: searchParams.get("hasta"),
      modulo:
        modulo && MODULES.includes(modulo as DashboardModule)
          ? (modulo as DashboardModule)
          : "convenios",
      tipo: readNumber(searchParams.get("tipo")),
      entidad: readNumber(searchParams.get("entidad")),
      ambito: readNumber(searchParams.get("ambito")),
      granularidad:
        granularidad && GRANULARITIES.includes(granularidad as Granularity)
          ? (granularidad as Granularity)
          : "mes",
    };
  }, [searchParams]);

  /** Aplica cambios parciales a la URL; los valores vacíos/nulos se omiten del querystring. */
  const setFilters = useCallback(
    (patch: Partial<DashboardFilters>) => {
      const next = new URLSearchParams(searchParams.toString());
      const apply = (key: string, value: string | number | null | undefined) => {
        if (value === null || value === undefined || value === "") {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      };

      if ("desde" in patch) apply("desde", patch.desde ?? null);
      if ("hasta" in patch) apply("hasta", patch.hasta ?? null);
      if ("modulo" in patch) apply("modulo", patch.modulo ?? null);
      if ("tipo" in patch) apply("tipo", patch.tipo ?? null);
      if ("entidad" in patch) apply("entidad", patch.entidad ?? null);
      if ("ambito" in patch) apply("ambito", patch.ambito ?? null);
      if ("granularidad" in patch) apply("gran", patch.granularidad ?? null);

      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return { filters, setFilters };
}
