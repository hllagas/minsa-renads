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

/**
 * Carga masiva de estudiantes desde `.xlsx` (`POST /students/bulk-upload/`, multipart, campo
 * `archivo`). Al éxito invalida la lista de estudiantes para que el CRUD refresque.
 */
export function useStudentsBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (archivo: File) => {
      const form = new FormData();
      form.append("archivo", archivo);
      return postMultipart<StudentBulkUploadResult>("students/bulk-upload/", form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("students") });
    },
  });
}
