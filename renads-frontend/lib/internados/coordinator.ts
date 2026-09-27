import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type Paginated } from "@/lib/api/client";
import type { CoordinatorSedeRead, CoordinatorTutorRead } from "@/lib/internados/types";

// ---------------------------------------------------------------------------
// Funciones de acceso a la API
// ---------------------------------------------------------------------------

/**
 * Lista todas las sedes asignadas a un coordinador.
 * Maneja: array directo, respuesta paginada DRF (`results`) u objeto inesperado → `[]`.
 */
export async function getCoordinatorSedes(
  coordinatorId: number,
): Promise<CoordinatorSedeRead[]> {
  const response = await api.get<
    CoordinatorSedeRead[] | Paginated<CoordinatorSedeRead> | Record<string, unknown>
  >(`/coordinators/${coordinatorId}/sedes/`);

  const data = response.data;

  // Caso 1: respuesta paginada DRF
  if (
    data &&
    typeof data === "object" &&
    "results" in data &&
    Array.isArray((data as Paginated<CoordinatorSedeRead>).results)
  ) {
    return (data as Paginated<CoordinatorSedeRead>).results;
  }

  // Caso 2: array directo
  if (Array.isArray(data)) {
    return data as CoordinatorSedeRead[];
  }

  // Caso 3: objeto inesperado
  console.warn(
    "[CoordinatorSede] El endpoint /coordinators/%d/sedes/ devolvió un objeto inesperado. Se retorna lista vacía.",
    coordinatorId,
    data,
  );
  return [];
}

/** Crea una sede (IPRESS) para un coordinador. La universidad se deriva del coordinador. */
export async function createCoordinatorSede(
  coordinatorId: number,
  payload: { ipress: string },
): Promise<CoordinatorSedeRead> {
  const response = await api.post<CoordinatorSedeRead>(
    `/coordinators/${coordinatorId}/sedes/`,
    payload,
  );
  return response.data;
}

/**
 * Elimina una sede de coordinador (cascade elimina sus tutores asignados).
 * El backend responde 204 (sin cuerpo).
 */
export async function deleteCoordinatorSede(
  coordinatorId: number,
  sedePk: number,
): Promise<void> {
  await api.delete(`/coordinators/${coordinatorId}/sedes/${sedePk}/`);
}

/**
 * Lista los tutores asignados a una sede de coordinador.
 * Maneja: array directo, respuesta paginada DRF (`results`) u objeto inesperado → `[]`.
 */
export async function getCoordinatorTutors(
  coordinatorId: number,
  sedePk: number,
): Promise<CoordinatorTutorRead[]> {
  const response = await api.get<
    CoordinatorTutorRead[] | Paginated<CoordinatorTutorRead> | Record<string, unknown>
  >(`/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/`);

  const data = response.data;

  // Caso 1: respuesta paginada DRF
  if (
    data &&
    typeof data === "object" &&
    "results" in data &&
    Array.isArray((data as Paginated<CoordinatorTutorRead>).results)
  ) {
    return (data as Paginated<CoordinatorTutorRead>).results;
  }

  // Caso 2: array directo
  if (Array.isArray(data)) {
    return data as CoordinatorTutorRead[];
  }

  // Caso 3: objeto inesperado
  console.warn(
    "[CoordinatorTutor] El endpoint /coordinators/%d/sedes/%d/tutores/ devolvió un objeto inesperado. Se retorna lista vacía.",
    coordinatorId,
    sedePk,
    data,
  );
  return [];
}

/** Asigna un tutor a una sede de coordinador. */
export async function createCoordinatorTutor(
  coordinatorId: number,
  sedePk: number,
  payload: { tutor: number },
): Promise<CoordinatorTutorRead> {
  const response = await api.post<CoordinatorTutorRead>(
    `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/`,
    payload,
  );
  return response.data;
}

/**
 * Desasigna un tutor de una sede de coordinador.
 * El backend responde 204 (sin cuerpo).
 */
export async function deleteCoordinatorTutor(
  coordinatorId: number,
  sedePk: number,
  tutorPk: number,
): Promise<void> {
  await api.delete(
    `/coordinators/${coordinatorId}/sedes/${sedePk}/tutores/${tutorPk}/`,
  );
}

// ---------------------------------------------------------------------------
// Hooks de TanStack Query
// ---------------------------------------------------------------------------

/** Lista las sedes asignadas al coordinador identificado por `coordinatorId`. */
export function useCoordinatorSedes(coordinatorId: number | null) {
  return useQuery({
    queryKey: ["coordinators", coordinatorId, "sedes"],
    queryFn: () => getCoordinatorSedes(coordinatorId!),
    enabled: coordinatorId != null,
  });
}

/** Mutación para agregar una sede (IPRESS) al coordinador. */
export function useAddCoordinatorSede(coordinatorId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { ipress: string }) =>
      createCoordinatorSede(coordinatorId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["coordinators", coordinatorId, "sedes"],
      });
    },
  });
}

/** Mutación para eliminar una sede (cascade elimina tutores de esa sede). */
export function useDeleteCoordinatorSede(coordinatorId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sedePk: number) => deleteCoordinatorSede(coordinatorId, sedePk),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["coordinators", coordinatorId, "sedes"],
      });
    },
  });
}

/** Lista los tutores asignados a la sede `sedePk` del coordinador. */
export function useCoordinatorTutors(
  coordinatorId: number | null,
  sedePk: number | null,
) {
  return useQuery({
    queryKey: ["coordinators", coordinatorId, "sedes", sedePk, "tutors"],
    queryFn: () => getCoordinatorTutors(coordinatorId!, sedePk!),
    enabled: coordinatorId != null && sedePk != null,
  });
}

/** Mutación para asignar un tutor a una sede del coordinador. */
export function useAddCoordinatorTutor(coordinatorId: number, sedePk: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { tutor: number }) =>
      createCoordinatorTutor(coordinatorId, sedePk, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["coordinators", coordinatorId, "sedes", sedePk, "tutors"],
      });
    },
  });
}

/** Mutación para desasignar un tutor de una sede del coordinador. */
export function useDeleteCoordinatorTutor(coordinatorId: number, sedePk: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tutorPk: number) =>
      deleteCoordinatorTutor(coordinatorId, sedePk, tutorPk),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["coordinators", coordinatorId, "sedes", sedePk, "tutors"],
      });
    },
  });
}

// ---------------------------------------------------------------------------
// Sedes disponibles
// ---------------------------------------------------------------------------

/** Respuesta de /coordinators/{id}/sedes-disponibles/ */
export interface SedeDisponible {
  id: string;       // codigo_renipress (PK textual)
  nombre: string;
}

/** Obtiene las sedes docentes disponibles para asignar al coordinador. */
export async function getSedesDisponibles(
  coordinatorId: number,
): Promise<SedeDisponible[]> {
  const response = await api.get<SedeDisponible[]>(
    `/coordinators/${coordinatorId}/sedes-disponibles/`,
  );
  return Array.isArray(response.data) ? response.data : [];
}

/** Hook TanStack Query para listar las sedes disponibles del coordinador. */
export function useSedesDisponibles(coordinatorId: number | null) {
  return useQuery({
    queryKey: ["coordinators", coordinatorId, "sedes-disponibles"],
    queryFn: () => getSedesDisponibles(coordinatorId!),
    enabled: coordinatorId != null,
  });
}
