"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api/schema";
import { createResourceHooks } from "@/lib/crud/hooks";
import { resourceKeys } from "@/lib/api/query";
import { postMultipart, postMultipartBlob } from "@/lib/api/upload";

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
 * Resultado de la carga masiva de estudiantes (RN-16, flujo F7 en dos pasos, all-or-nothing).
 * `bulk-upload` responde `201 { creados }` solo cuando la trama está limpia.
 */
export interface StudentBulkUploadResult {
  creados: number;
}

/**
 * Resultado de la **pre-validación** (`POST /students/bulk-validate/`). Si la trama está limpia
 * devuelve `{ valido: true, filas }`; si tiene inconsistencias, el backend responde el mismo
 * `.xlsx` con las celdas resaltadas, que aquí se expone como `Blob` para descargar.
 */
export type StudentBulkValidateResult =
  | { valido: true; filas: number }
  | { valido: false; blob: Blob; filename: string; errores: number };

export interface StudentBulkUploadParams {
  archivo: File;
  /** Universidad fijada en el filtro de la vista (siempre disponible cuando el dialog está visible). */
  universidadId?: number | null;
  /** Periodo de internado (solo PREGRADO). */
  periodoId?: number | null;
}

function _bulkForm({ archivo, universidadId, periodoId }: StudentBulkUploadParams): FormData {
  const form = new FormData();
  form.append("archivo", archivo);
  if (universidadId != null) form.append("universidad_id", String(universidadId));
  if (periodoId != null) form.append("periodo_internado_id", String(periodoId));
  return form;
}

/**
 * Pre-validación de la trama sin escribir en BD (`POST /students/bulk-validate/`, RN-16 / F7).
 * Distingue por `Content-Type`: JSON ⇒ trama válida; hoja de cálculo ⇒ archivo anotado con las
 * celdas a corregir (se entrega como `Blob`).
 */
export function useStudentsBulkValidate() {
  return useMutation({
    mutationFn: async (params: StudentBulkUploadParams): Promise<StudentBulkValidateResult> => {
      const res = await postMultipartBlob("students/bulk-validate/", _bulkForm(params));
      const contentType = String(res.headers["content-type"] ?? "");
      if (contentType.includes("application/json")) {
        const json = JSON.parse(await res.data.text()) as { filas?: number };
        return { valido: true, filas: json.filas ?? 0 };
      }
      const dispo = String(res.headers["content-disposition"] ?? "");
      const filename =
        dispo.match(/filename="?([^"]+)"?/)?.[1] ?? "TramaCargaMasivaEstudiantes_observada.xlsx";
      const errores = Number(res.headers["x-validation-errors"] ?? 0);
      return { valido: false, blob: res.data, filename, errores };
    },
  });
}

/**
 * Carga masiva de estudiantes desde `.xlsx` (`POST /students/bulk-upload/`, multipart).
 * All-or-nothing: crea todo solo si la trama está limpia (usar tras `useStudentsBulkValidate`).
 * Envía `universidad_id` y `periodo_internado_id` tomados de los filtros activos de la vista.
 */
export function useStudentsBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: StudentBulkUploadParams) =>
      postMultipart<StudentBulkUploadResult>("students/bulk-upload/", _bulkForm(params)),
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
