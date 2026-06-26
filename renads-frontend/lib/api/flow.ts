"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { resourceKeys } from "@/lib/api/query";

/**
 * Mutación de una acción de flujo sobre un recurso (`/{endpoint}/{id}/{action}/`). Genérico:
 * sirve para convenios, internados, rotaciones, etc. Invalida el detalle y las listas de flujo.
 */
export function useResourceAction(endpoint: string, id: number, action: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const { data } = await api.post(`/${endpoint}/${id}/${action}/`, payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.detail(endpoint, id) });
      qc.invalidateQueries({ queryKey: [endpoint, "flow", id] });
    },
  });
}

/** Lista de un sub-recurso de flujo (GET `/{endpoint}/{id}/{sub}/`). Devuelve un array. */
export function useResourceSubList<T = Record<string, unknown>>(
  endpoint: string,
  id: number,
  sub: string,
) {
  return useQuery({
    queryKey: [endpoint, "flow", id, sub],
    queryFn: async () => {
      const { data } = await api.get<T[]>(`/${endpoint}/${id}/${sub}/`);
      return data;
    },
    enabled: id > 0,
  });
}
