"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchAllPages } from "@/lib/dashboard/fetch-all";

/** Forma mínima de un item de catálogo (estados/tipos) del backend. */
interface CatalogItem {
  id: number;
  codigo?: string;
  nombre?: string;
  /** Orden en el flujo (estados); ausente en algunos catálogos. */
  orden?: number;
}

/** Mapa de etiquetas/orden de un catálogo, resuelto desde el backend (no hardcodear nombres). */
export interface CatalogLabels {
  /** Etiqueta legible por `codigo` (cae al propio código si no hay nombre). */
  label: (codigo: string) => string;
  /** Orden de flujo por `codigo` (Infinity si el catálogo no define orden). */
  order: (codigo: string) => number;
  isLoading: boolean;
}

/**
 * Carga un catálogo (estados/tipos) y expone etiqueta + orden por `codigo`. `staleTime` largo:
 * los catálogos cambian rara vez. Reutiliza la Vía A para traer todas las filas del catálogo.
 */
export function useCatalogLabels(endpoint: string): CatalogLabels {
  const query = useQuery({
    queryKey: ["dashboard", "catalog", endpoint],
    queryFn: () => fetchAllPages<CatalogItem>(endpoint),
    staleTime: 10 * 60_000,
  });

  const items = query.data?.results ?? [];
  const byCode = new Map<string, CatalogItem>();
  for (const item of items) {
    if (item.codigo) byCode.set(item.codigo, item);
  }

  return {
    label: (codigo: string) => byCode.get(codigo)?.nombre ?? codigo,
    order: (codigo: string) => byCode.get(codigo)?.orden ?? Number.POSITIVE_INFINITY,
    isLoading: query.isLoading,
  };
}
