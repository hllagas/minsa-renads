"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api/schema";
import { createResourceHooks } from "@/lib/crud/hooks";
import { resourceKeys } from "@/lib/api/query";
import { postMultipart } from "@/lib/api/upload";

export type InternshipRead = components["schemas"]["InternshipRead"];
export type InternshipWrite = components["schemas"]["InternshipWrite"];
export type RotationRead = components["schemas"]["RotationRead"];

/** Hooks CRUD de internados (read = InternshipRead, write = InternshipWrite). */
export const internshipHooks = createResourceHooks<InternshipRead, InternshipWrite>(
  "interns",
);

/** Hooks de lectura de rotaciones (la escritura va por acciones de flujo). */
export const rotationHooks = createResourceHooks<RotationRead, Record<string, unknown>>(
  "rotations",
);

/**
 * Resultado de la carga masiva de estudiantes (RN-16). Tipado a mano: el OpenAPI declara la
 * respuesta como `StudentBulkUpload` (que solo modela el request `{ archivo }`) — es impreciso.
 * La forma real la define `docs/api-internados.md` §Carga masiva.
 */
export interface StudentBulkUploadResult {
  creados: number;
  omitidos: number;
  errores: { fila: number; motivo: string }[];
}

export interface StudentBulkUploadParams {
  archivo: File;
  /** Universidad fijada en el filtro de la vista (siempre disponible cuando el dialog está visible). */
  universidadId?: number | null;
  /** Periodo de internado (solo PREGRADO). */
  periodoId?: number | null;
}

/**
 * Carga masiva de estudiantes desde `.xlsx` (`POST /students/bulk-upload/`, multipart).
 * Envía `universidad_id` y `periodo_internado_id` tomados de los filtros activos de la vista.
 */
export function useStudentsBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ archivo, universidadId, periodoId }: StudentBulkUploadParams) => {
      const form = new FormData();
      form.append("archivo", archivo);
      if (universidadId != null) form.append("universidad_id", String(universidadId));
      if (periodoId != null) form.append("periodo_internado_id", String(periodoId));
      return postMultipart<StudentBulkUploadResult>("students/bulk-upload/", form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("students") });
    },
  });
}

/** Resultado de la carga masiva de internos. */
export interface InternsBulkUploadResult {
  creados: number;
  omitidos: number;
  errores: { fila: number; motivo: string }[];
}

/**
 * Carga masiva de internos desde `.xlsx` (`POST /interns/bulk-upload/`, multipart, campos
 * `archivo` + `convenio`). Al éxito invalida la lista de internos.
 */
export function useInternsBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ archivo, convenio }: { archivo: File; convenio: number }) => {
      const form = new FormData();
      form.append("archivo", archivo);
      form.append("convenio", String(convenio));
      return postMultipart<InternsBulkUploadResult>("interns/bulk-upload/", form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("interns") });
    },
  });
}
