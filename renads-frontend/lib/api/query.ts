import { api, type Paginated } from "@/lib/api/client";

/** Parámetros comunes de listado (DRF: PageNumberPagination + django-filter + ordering/search). */
export interface ListParams {
  page?: number;
  ordering?: string;
  search?: string;
  /** Filtros por campo (django-filter). Valores `undefined`/`""`/`null` se omiten. */
  filters?: Record<string, string | number | boolean | null | undefined>;
}

/** Construye los query params de un listado, omitiendo vacíos. */
export function buildListParams(params: ListParams): Record<string, string> {
  const out: Record<string, string> = {};
  if (params.page && params.page > 1) out.page = String(params.page);
  if (params.ordering) out.ordering = params.ordering;
  if (params.search) out.search = params.search;
  for (const [k, v] of Object.entries(params.filters ?? {})) {
    if (v === undefined || v === null || v === "") continue;
    out[k] = String(v);
  }
  return out;
}

/** Registro con id numérico (mínimo que requiere el cliente CRUD). */
export interface HasId {
  id: number;
}

/** Registro genérico indexable (entidades/catálogos sin tipo específico, para el CRUD declarativo). */
export interface WithId extends HasId {
  [key: string]: unknown;
}

/**
 * Cliente CRUD para un recurso DRF (`<endpoint>/`). Centraliza las llamadas Axios; nunca usar
 * Axios directo en componentes. Tipado por el llamador con los tipos de `lib/api/schema.d.ts`.
 */
export function createResourceApi<TRead extends HasId, TWrite = Partial<TRead>>(
  endpoint: string,
) {
  const base = `/${endpoint}/`;
  return {
    endpoint,
    async list(params: ListParams = {}): Promise<Paginated<TRead>> {
      const { data } = await api.get<Paginated<TRead>>(base, {
        params: buildListParams(params),
      });
      return data;
    },
    async retrieve(id: number): Promise<TRead> {
      const { data } = await api.get<TRead>(`${base}${id}/`);
      return data;
    },
    async create(payload: TWrite): Promise<TRead> {
      const { data } = await api.post<TRead>(base, payload);
      return data;
    },
    async update(id: number, payload: Partial<TWrite>): Promise<TRead> {
      const { data } = await api.patch<TRead>(`${base}${id}/`, payload);
      return data;
    },
    async remove(id: number): Promise<void> {
      await api.delete(`${base}${id}/`);
    },
  };
}

export type ResourceApi<TRead extends HasId, TWrite = Partial<TRead>> = ReturnType<
  typeof createResourceApi<TRead, TWrite>
>;

/** Keys de TanStack Query por recurso. */
export const resourceKeys = {
  all: (endpoint: string) => [endpoint] as const,
  list: (endpoint: string, params: ListParams) =>
    [endpoint, "list", buildListParams(params)] as const,
  detail: (endpoint: string, id: number) => [endpoint, "detail", id] as const,
};
