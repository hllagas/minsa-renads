import { api, type Paginated } from "@/lib/api/client";
import { buildListParams, type ListParams } from "@/lib/api/query";

/** Resultado de una carga completa de la Vía A (lista acumulada + aviso de truncamiento). */
export interface FetchAllResult<T> {
  results: T[];
  /** `true` si se alcanzó el tope de seguridad y los datos están truncados. */
  truncated: boolean;
  /** Total reportado por el backend (`count`) en la primera página. */
  count: number;
}

/** Tope de seguridad de páginas a recorrer (evita traer datasets enormes en la Vía A). */
const MAX_PAGES = 25;

/**
 * Tamaño de página solicitado. El backend fija `PAGE_SIZE=20`; aquí pedimos uno mayor para reducir
 * el nº de peticiones. Si el backend ignora `page_size`, la paginación sigue funcionando por `page`.
 */
// TODO(contrato): confirmar si el backend admite `page_size` (backend-overview.md solo documenta
// `?page=N`). Si lo ignora, este valor es inocuo y solo cambia el nº de peticiones.
const PAGE_SIZE = 100;

/**
 * Recorre la paginación DRF de un endpoint de lista acumulando todos los `results` dentro de los
 * filtros dados (Vía A: agregación en cliente). Se detiene al agotar `next` o al tope `MAX_PAGES`,
 * señalando truncamiento. Usa el cliente Axios único (`lib/api/`); nunca llamar Axios en componentes.
 */
export async function fetchAllPages<T>(
  endpoint: string,
  filters: ListParams["filters"] = {},
  ordering?: string,
): Promise<FetchAllResult<T>> {
  const base = `/${endpoint}/`;
  const results: T[] = [];
  let count = 0;
  let truncated = false;

  for (let page = 1; page <= MAX_PAGES; page++) {
    const params = {
      ...buildListParams({ page, ordering, filters }),
      page_size: String(PAGE_SIZE),
    };
    const { data } = await api.get<Paginated<T>>(base, { params });
    if (page === 1) count = data.count;
    results.push(...data.results);

    if (!data.next) {
      return { results, truncated: false, count };
    }
    if (page === MAX_PAGES) {
      truncated = true;
    }
  }

  return { results, truncated, count };
}
