import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { resourceKeys } from "@/lib/api/query";
import type { Documento } from "@/lib/api/documents";

/** Resultado de las acciones de generación de PDF (mismo shape que `Documento`). */
export type GenerarPdfResult = Documento;

/**
 * Genera el PDF del proyecto del convenio.
 * POST /conventions/{id}/generar-proyecto/ → Documento
 * Requiere rol `Administrador RENADS` o `DIGEP`.
 */
export function useGenerarProyecto(convenioId: number) {
  const qc = useQueryClient();
  return useMutation<GenerarPdfResult, unknown, void>({
    mutationFn: async () => {
      const { data } = await api.post<GenerarPdfResult>(
        `/conventions/${convenioId}/generar-proyecto/`,
        {},
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("documents") });
      qc.invalidateQueries({
        queryKey: resourceKeys.detail("conventions", convenioId),
      });
    },
  });
}

/**
 * Genera el PDF del expediente del convenio.
 * POST /conventions/{id}/generar-expediente/ → Documento
 * Requiere rol `Administrador RENADS` o `DIGEP`.
 */
export function useGenerarExpediente(convenioId: number) {
  const qc = useQueryClient();
  return useMutation<GenerarPdfResult, unknown, void>({
    mutationFn: async () => {
      const { data } = await api.post<GenerarPdfResult>(
        `/conventions/${convenioId}/generar-expediente/`,
        {},
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("documents") });
      qc.invalidateQueries({
        queryKey: resourceKeys.detail("conventions", convenioId),
      });
    },
  });
}
