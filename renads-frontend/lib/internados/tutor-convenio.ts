import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import type { TutorConvenioRead } from "@/lib/internados/types";

// ---------------------------------------------------------------------------
// Funciones de acceso a la API
// ---------------------------------------------------------------------------

/**
 * Lista todos los vínculos TutorConvenio de un tutor.
 * El endpoint puede devolver: array directo, respuesta paginada `{ count, results }` o,
 * en caso de que el schema generado sea incorrecto, un objeto con campos de Tutor.
 */
export async function getTutorConvenios(tutorId: number): Promise<TutorConvenioRead[]> {
  const response = await api.get<
    TutorConvenioRead[] | Paginated<TutorConvenioRead> | Record<string, unknown>
  >(`/tutors/${tutorId}/convenios/`);

  const data = response.data;

  // Caso 1: respuesta paginada DRF
  if (data && typeof data === "object" && "results" in data && Array.isArray((data as Paginated<TutorConvenioRead>).results)) {
    return (data as Paginated<TutorConvenioRead>).results;
  }

  // Caso 2: array directo
  if (Array.isArray(data)) {
    return data as TutorConvenioRead[];
  }

  // Caso 3: el schema devuelve el objeto Tutor en lugar del sub-recurso (bug de contrato)
  // En este caso no hay datos de vínculos; retornamos vacío y avisamos.
  console.warn(
    "[TutorConvenio] El endpoint /tutors/%d/convenios/ devolvió un objeto inesperado (posible bug de schema). Se retorna lista vacía.",
    tutorId,
    data,
  );
  return [];
}

/** Crea un vínculo tutor × convenio × IPRESS. */
export async function createTutorConvenio(
  tutorId: number,
  payload: { convenio: number; ipress: string },
): Promise<TutorConvenioRead> {
  const response = await api.post<TutorConvenioRead>(
    `/tutors/${tutorId}/convenios/`,
    payload,
  );
  return response.data;
}

/**
 * Elimina un vínculo TutorConvenio.
 * El backend responde 204 (sin cuerpo).
 */
export async function deleteTutorConvenio(
  tutorId: number,
  convenioPk: number,
): Promise<void> {
  await api.delete(`/tutors/${tutorId}/convenios/${convenioPk}/`);
}

// ---------------------------------------------------------------------------
// Hooks de TanStack Query
// ---------------------------------------------------------------------------

/** Lista los vínculos TutorConvenio del tutor identificado por `tutorId`. */
export function useTutorConvenios(tutorId: number | null) {
  return useQuery({
    queryKey: ["tutors", tutorId, "convenios"],
    queryFn: () => getTutorConvenios(tutorId!),
    enabled: tutorId != null && tutorId > 0,
  });
}

/** Mutación para crear un nuevo vínculo tutor × convenio × IPRESS. */
export function useAddTutorConvenio(tutorId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { convenio: number; ipress: string }) =>
      createTutorConvenio(tutorId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tutors", tutorId, "convenios"] });
    },
  });
}

/** Mutación para eliminar un vínculo TutorConvenio. */
export function useDeleteTutorConvenio(tutorId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (convenioPk: number) => deleteTutorConvenio(tutorId, convenioPk),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tutors", tutorId, "convenios"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Hook auxiliar: resolución de ids de tipo y estado de convenio
// ---------------------------------------------------------------------------

/**
 * Resuelve en runtime los ids de tipo «Específico» y estados «vigentes»
 * (`VIGENTE`/`PUBLICADO`/`SUSCRITO`) para filtrar convenios en el select.
 * Patrón: `app/(app)/internados/internos/page.tsx`.
 */
export function useConvenioEspecificoIds() {
  const tiposQuery = useQuery({
    queryKey: ["convention-types", "all"],
    queryFn: () =>
      api.get<Paginated<WithId>>("/convention-types/").then((r) => r.data.results),
    staleTime: 30 * 60_000,
  });

  const estadosQuery = useQuery({
    queryKey: ["convention-statuses", "all"],
    queryFn: () =>
      api.get<Paginated<WithId>>("/convention-statuses/").then((r) => r.data.results),
    staleTime: 30 * 60_000,
  });

  const match = (rows: WithId[] | undefined, needle: string): number | undefined =>
    rows
      ?.find((r) => `${r.codigo ?? ""} ${r.nombre ?? ""}`.toLowerCase().includes(needle))
      ?.id as number | undefined;

  const especificoId = useMemo(
    () => match(tiposQuery.data, "espec"),
    [tiposQuery.data],
  );

  const vigenteId = useMemo(
    () => match(estadosQuery.data, "vigente"),
    [estadosQuery.data],
  );

  return { especificoId, vigenteId, isLoading: tiposQuery.isLoading || estadosQuery.isLoading };
}
