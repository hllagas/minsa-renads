"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Paginated } from "@/lib/api/client";
import { buildListParams, resourceKeys, type HasId, type ListParams } from "@/lib/api/query";

const ENDPOINT = "documents";
const base = `/${ENDPOINT}/`;

/** Documento (gestión documental polimórfica + versionado). Campos de lectura del contrato (§4). */
export interface Documento extends HasId {
  id: number;
  tipo_documento: number;
  tipo_documento_nombre: string;
  tipo_contenido: number;
  tipo_contenido_label: string;
  id_objeto: number;
  referencia_externa: string;
  nombre_archivo: string;
  version: number;
  estado: string;
  version_anterior: number | null;
  cargado_por: number | string | null;
  cargado_en: string;
}

/** Campos de escritura (POST). `version`/`estado`/`version_anterior` los fija el backend. */
export interface DocumentoWrite {
  tipo_contenido: number;
  id_objeto: number;
  tipo_documento: number;
  nombre_archivo: string;
  referencia_externa: string;
}

/** Cliente Axios del recurso `documents` (solo en `lib/api/`). */
export const documentsApi = {
  async list(params: ListParams = {}): Promise<Paginated<Documento>> {
    const { data } = await api.get<Paginated<Documento>>(base, {
      params: buildListParams(params),
    });
    return data;
  },
  async retrieve(id: number): Promise<Documento> {
    const { data } = await api.get<Documento>(`${base}${id}/`);
    return data;
  },
  // TODO(v2 content-types): habilitar `create` cuando el backend exponga `content-types`
  // (se necesita resolver `tipo_contenido` + el `id_objeto` del objeto padre).
  async create(payload: DocumentoWrite): Promise<Documento> {
    const { data } = await api.post<Documento>(base, payload);
    return data;
  },
  async remove(id: number): Promise<void> {
    await api.delete(`${base}${id}/`);
  },
  /** Acción `url-descarga`: devuelve la referencia firmada del documento. */
  async downloadUrl(id: number): Promise<{ url: string }> {
    const { data } = await api.get<{ url: string }>(`${base}${id}/url-descarga/`);
    return data;
  },
};

/** Lista paginada de documentos (TanStack Query). */
export function useDocumentsList(params: ListParams = {}) {
  return useQuery({
    queryKey: resourceKeys.list(ENDPOINT, params),
    queryFn: () => documentsApi.list(params),
  });
}

/** Elimina un documento e invalida la lista. */
export function useRemoveDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => documentsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: resourceKeys.all(ENDPOINT) }),
  });
}

/** Resuelve la URL de descarga de un documento (acción puntual, no se cachea). */
export function useDocumentDownloadUrl() {
  return useMutation({
    mutationFn: (id: number) => documentsApi.downloadUrl(id),
  });
}
