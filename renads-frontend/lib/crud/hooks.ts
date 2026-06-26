"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createResourceApi,
  resourceKeys,
  type HasId,
  type ListParams,
} from "@/lib/api/query";

/**
 * Genera hooks CRUD de TanStack Query para un recurso DRF. Patrón único reutilizable por
 * entidades, catálogos y convenios. Tipar con los tipos de `lib/api/schema.d.ts`.
 */
export function createResourceHooks<TRead extends HasId, TWrite = Partial<TRead>>(
  endpoint: string,
) {
  const apiRes = createResourceApi<TRead, TWrite>(endpoint);

  function useList(params: ListParams = {}) {
    return useQuery({
      queryKey: resourceKeys.list(endpoint, params),
      queryFn: () => apiRes.list(params),
      placeholderData: keepPreviousData, // evita parpadeo al paginar/filtrar
    });
  }

  function useDetail(id: number | null) {
    return useQuery({
      queryKey: resourceKeys.detail(endpoint, id ?? -1),
      queryFn: () => apiRes.retrieve(id as number),
      enabled: id != null,
    });
  }

  function useCreate() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (payload: TWrite) => apiRes.create(payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: resourceKeys.all(endpoint) }),
    });
  }

  function useUpdate() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: ({ id, payload }: { id: number; payload: Partial<TWrite> }) =>
        apiRes.update(id, payload),
      onSuccess: () => qc.invalidateQueries({ queryKey: resourceKeys.all(endpoint) }),
    });
  }

  function useRemove() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (id: number) => apiRes.remove(id),
      onSuccess: () => qc.invalidateQueries({ queryKey: resourceKeys.all(endpoint) }),
    });
  }

  return { api: apiRes, useList, useDetail, useCreate, useUpdate, useRemove };
}

export type ResourceHooks<TRead extends HasId, TWrite = Partial<TRead>> = ReturnType<
  typeof createResourceHooks<TRead, TWrite>
>;
