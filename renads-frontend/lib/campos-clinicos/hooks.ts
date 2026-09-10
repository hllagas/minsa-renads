"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { resourceKeys } from "@/lib/api/query";
import { postMultipart } from "@/lib/api/upload";

export interface ClinicalBulkUploadResult {
  creados: number;
  omitidos: number;
  errores: { fila: number; motivo: string }[];
}

/** Carga masiva de determinaciones (`POST /clinical-field-registrations/bulk-upload/`). */
export function useClinicalRegistrationsBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (archivo: File) => {
      const form = new FormData();
      form.append("archivo", archivo);
      return postMultipart<ClinicalBulkUploadResult>(
        "clinical-field-registrations/bulk-upload/",
        form,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("clinical-field-registrations") });
    },
  });
}

/** Carga masiva de asignaciones (`POST /clinical-field-allocations/bulk-upload/`). */
export function useClinicalAllocationsBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (archivo: File) => {
      const form = new FormData();
      form.append("archivo", archivo);
      return postMultipart<ClinicalBulkUploadResult>(
        "clinical-field-allocations/bulk-upload/",
        form,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("clinical-field-allocations") });
    },
  });
}
