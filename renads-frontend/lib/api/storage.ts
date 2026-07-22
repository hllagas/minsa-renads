"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { postMultipart } from "@/lib/api/upload";
import { resourceKeys } from "@/lib/api/query";
import type { Documento } from "@/lib/api/documents";

/** Tamaño máximo por archivo (25 MiB, `GCS_MAX_UPLOAD_BYTES`). Validación cliente (UX). */
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

/** Content-types y accept del `<input type=file>` por tipo de adjunto (ver docs/api-almacenamiento.md). */
export const LOGO_ACCEPT = "image/png,image/jpeg,image/webp";
export const ANNEX_ACCEPT = "application/pdf";

/** Entidades con logo (`upload-logo`/`logo-url`). Sin versionado (una sola `referencia_logo`). */
export const LOGO_ENTITIES = [
  "universities",
  "regional-governments",
  "regional-organs",
  "executing-units",
  "ipress",
] as const;
export type LogoEntity = (typeof LOGO_ENTITIES)[number];

/** ¿El endpoint soporta logo? */
export function hasLogo(endpoint: string): endpoint is LogoEntity {
  return (LOGO_ENTITIES as readonly string[]).includes(endpoint);
}

/**
 * Entidades con anexos (`annex-checklist`/`annex-upload`) y su `tipo_actor`.
 * Refactor 2026-07: las declaraciones juradas del interno (`INTERNO`) se adjuntan sobre el
 * **internado** (`interns/{id}/…`), no sobre el estudiante. El endpoint `students` ya no expone anexos.
 */
export const ANNEX_ENTITIES = {
  interns: "INTERNO",
  "university-authorities": "AUTORIDAD_UNIVERSIDAD",
  representatives: "REPRESENTANTE",
} as const;
export type AnnexEntity = keyof typeof ANNEX_ENTITIES;

/** ¿El endpoint soporta anexos? */
export function hasAnnexes(endpoint: string): endpoint is AnnexEntity {
  return endpoint in ANNEX_ENTITIES;
}

export interface LogoUploadResult {
  referencia_logo: string;
  url: string;
}
export interface LogoUrlResult {
  url: string;
}

/** Ítem del checklist de anexos de un actor (forma exacta del contrato §Anexos). */
export interface AnnexChecklistItem {
  documento_anexo: number;
  codigo: string;
  nombre: string;
  obligatorio: boolean;
  adjuntado: boolean;
  documento_id: number | null;
  version: number | null;
  referencia_externa: string | null;
}

/** Cliente Axios de los adjuntos reales (solo vive en `lib/api/`). */
export const storageApi = {
  /** Sube/reemplaza el logo de una entidad. Campo multipart `archivo`. */
  async uploadLogo(entidad: string, id: number, archivo: File): Promise<LogoUploadResult> {
    const form = new FormData();
    form.append("archivo", archivo);
    return postMultipart<LogoUploadResult>(`${entidad}/${id}/upload-logo/`, form);
  },
  /** Signed URL del logo bajo demanda (`404` si la entidad no tiene logo). */
  async getLogoUrl(entidad: string, id: number): Promise<LogoUrlResult> {
    const { data } = await api.get<LogoUrlResult>(`/${entidad}/${id}/logo-url/`);
    return data;
  },
  /** Checklist de anexos requeridos/adjuntados del actor. */
  async getAnnexChecklist(entidad: string, id: number): Promise<AnnexChecklistItem[]> {
    const { data } = await api.get<AnnexChecklistItem[]>(`/${entidad}/${id}/annex-checklist/`);
    return data;
  },
  /** Adjunta (o versiona) un anexo PDF. Re-subir el mismo `documento_anexo` crea `version = n+1`. */
  async uploadAnnex(
    entidad: string,
    id: number,
    vars: { documento_anexo: number; archivo: File; nombre_archivo?: string },
  ): Promise<Documento> {
    const form = new FormData();
    form.append("documento_anexo", String(vars.documento_anexo));
    form.append("archivo", vars.archivo);
    if (vars.nombre_archivo) form.append("nombre_archivo", vars.nombre_archivo);
    return postMultipart<Documento>(`${entidad}/${id}/annex-upload/`, form);
  },
};

/** Keys de cache de los adjuntos. */
export const logoKey = (entidad: string, id: number) => ["logo", entidad, id] as const;
export const annexChecklistKey = (entidad: string, id: number) =>
  ["annex-checklist", entidad, id] as const;

/**
 * Signed URL del logo (TanStack Query). `enabled=false` cuando la entidad no tiene `referencia_logo`
 * (evita un `404` innecesario). `retry:false` porque el `404` = sin logo. `staleTime` < 15 min
 * (expiración del signed URL) para no re-pedir en cada render pero refrescar antes de caducar.
 */
export function useLogoUrl(entidad: string, id: number, enabled = true) {
  return useQuery({
    queryKey: logoKey(entidad, id),
    queryFn: () => storageApi.getLogoUrl(entidad, id),
    enabled: enabled && id > 0,
    retry: false,
    staleTime: 10 * 60_000,
    gcTime: 12 * 60_000,
  });
}

/** Sube/reemplaza el logo; refresca su signed URL y la lista de la entidad (columna «Logo»). */
export function useUploadLogo(entidad: string, id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (archivo: File) => storageApi.uploadLogo(entidad, id, archivo),
    onSuccess: (data) => {
      qc.setQueryData(logoKey(entidad, id), { url: data.url } satisfies LogoUrlResult);
      qc.invalidateQueries({ queryKey: resourceKeys.all(entidad) });
    },
  });
}

/** Checklist de anexos del actor (TanStack Query). */
export function useAnnexChecklist(entidad: string, id: number, enabled = true) {
  return useQuery({
    queryKey: annexChecklistKey(entidad, id),
    queryFn: () => storageApi.getAnnexChecklist(entidad, id),
    enabled: enabled && id > 0,
  });
}

/** Adjunta/versiona un anexo; refresca el checklist y la lista de la entidad. */
export function useUploadAnnex(entidad: string, id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { documento_anexo: number; archivo: File; nombre_archivo?: string }) =>
      storageApi.uploadAnnex(entidad, id, vars),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: annexChecklistKey(entidad, id) });
      qc.invalidateQueries({ queryKey: resourceKeys.all(entidad) });
    },
  });
}
