"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { setUserPassword } from "@/lib/api/users";
import {
  assignUserProfiles,
  listAssignableEntityTypes,
  listUserProfiles,
  revokeUserProfile,
} from "@/lib/api/user-profiles";
import { resourceKeys } from "@/lib/api/query";
import type { AssignProfilesPayload } from "@/lib/usuarios/types";

/**
 * Mutación para cambiar la contraseña de un usuario (acción `set-password`). Invalida la lista de
 * usuarios al tener éxito. La contraseña no se persiste en estado de cliente ni se cachea.
 */
export function useSetPassword() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      setUserPassword(id, password),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: resourceKeys.all("users") }),
  });
}

/** Clave base de los perfiles de un usuario (invalidación parcial cubre `incluirInactivos`). */
const userProfilesKey = (userId: number) => ["users", userId, "profiles"] as const;

/**
 * Tipos de entidad asignables (`GET /profile-entity-types/`). Casi estático: `staleTime` alto.
 */
export function useAssignableEntityTypes() {
  return useQuery({
    queryKey: ["profile-entity-types"],
    queryFn: listAssignableEntityTypes,
    staleTime: 30 * 60_000,
  });
}

/** Perfiles (alcance) de un usuario. Solo consulta si hay `userId`. */
export function useUserProfiles(userId: number | null, incluirInactivos = false) {
  return useQuery({
    queryKey: [...userProfilesKey(userId ?? 0), { incluirInactivos }],
    queryFn: () => listUserProfiles(userId as number, { incluirInactivos }),
    enabled: userId != null,
  });
}

/** Asigna/reactiva perfiles de un usuario; invalida su lista de perfiles al tener éxito. */
export function useAssignUserProfiles(userId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: AssignProfilesPayload) => assignUserProfiles(userId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: userProfilesKey(userId) }),
  });
}

/** Da de baja (lógica) un perfil de un usuario; invalida su lista de perfiles al tener éxito. */
export function useRevokeUserProfile(userId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profileId: number) => revokeUserProfile(userId, profileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: userProfilesKey(userId) }),
  });
}
