import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";

/**
 * Búsqueda server-side de un recurso para selects/combobox (`/{endpoint}/?search=`).
 * Devuelve la primera página de resultados.
 */
export async function searchResource(
  endpoint: string,
  options: { search?: string; params?: Record<string, string> } = {},
): Promise<WithId[]> {
  const { data } = await api.get<Paginated<WithId>>(`/${endpoint}/`, {
    params: { ...options.params, search: options.search || undefined },
  });
  return data.results;
}

/** Detalle de un recurso por PK (numérica o textual) para resolver la etiqueta seleccionada. */
export async function getResourceItem(
  endpoint: string,
  id: string | number,
): Promise<WithId> {
  const { data } = await api.get<WithId>(`/${endpoint}/${id}/`);
  return data;
}
