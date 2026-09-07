import { useQuery } from "@tanstack/react-query";

import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";

/**
 * Catálogo canónico `organs` (5 filas) usado como discriminador de `OrganDirectory`
 * (FK `organo`). Los ids dependen de la BD, así que el front los resuelve por `nombre`
 * (nunca se hardcodean). Ver `docs/api-catalogos.md §2`.
 */
export interface Organ extends WithId {
  nombre: string;
  estado?: boolean;
}

/** Nombres canónicos de la tabla `organs` (fuente de verdad del backend). */
export const ORGAN_NOMBRE = {
  MINSA: "MINSA Administrativo",
  UNIVERSIDAD: "Universidad",
  GORE: "Gobierno Regional",
  UE: "Unidad Ejecutora",
  DIRIS: "MINSA DIRIS",
} as const;

/** Lista completa del catálogo `organs` (5 filas; cacheada largo — es canónico). */
export function useOrgans() {
  return useQuery({
    queryKey: ["organs", "all"],
    queryFn: async (): Promise<Organ[]> => {
      const { data } = await api.get<Paginated<Organ>>("/organs/", {
        params: { page: "1" },
      });
      return data.results;
    },
    staleTime: 30 * 60_000,
  });
}

/** Resuelve el `id` de un `Organ` por su `nombre` exacto (o `undefined`). */
export function organIdByNombre(
  organs: Organ[] | undefined,
  nombre: string,
): number | undefined {
  return organs?.find((o) => o.nombre === nombre)?.id;
}
