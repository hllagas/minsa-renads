"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { components } from "@/lib/api/schema";
import { createResourceHooks } from "@/lib/crud/hooks";
import { resourceKeys } from "@/lib/api/query";
import { postMultipart } from "@/lib/api/upload";

export type ConventionRead = components["schemas"]["ConventionRead"];
export type ConventionWrite = components["schemas"]["ConventionWrite"];

/** Hooks CRUD del recurso `conventions` (lectura = ConventionRead, escritura = ConventionWrite). */
export const conventionHooks = createResourceHooks<ConventionRead, ConventionWrite>(
  "conventions",
);

export interface ConventionsBulkUploadResult {
  creados: number;
  omitidos: number;
  errores: { fila: number; motivo: string }[];
}

/** Carga masiva de convenios (`POST /conventions/bulk-upload/`). Solo `Administrador RENADS`. */
export function useConventionsBulkUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (archivo: File) => {
      const form = new FormData();
      form.append("archivo", archivo);
      return postMultipart<ConventionsBulkUploadResult>("conventions/bulk-upload/", form);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("conventions") });
    },
  });
}
