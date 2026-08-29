import { api } from "@/lib/api/client";
import type {
  AssignProfilesPayload,
  AssignableEntityType,
  UserProfileRead,
} from "@/lib/usuarios/types";

/**
 * Capa API del alcance por objeto de un usuario (`UserEntityProfile`). Consume el sub-recurso
 * `users/{id}/profiles/` (backend T10) y el lookup `profile-entity-types/` (T11). Solo superusuario.
 * Nunca usar Axios directo en componentes: estas funciones envuelven el cliente único.
 */

/** `GET /users/{id}/profiles/` — perfiles (alcance) del usuario. Respuesta NO paginada (lista). */
export async function listUserProfiles(
  userId: number,
  opts: { incluirInactivos?: boolean } = {},
): Promise<UserProfileRead[]> {
  const { data } = await api.get<UserProfileRead[]>(`/users/${userId}/profiles/`, {
    params: opts.incluirInactivos ? { incluir_inactivos: "true" } : undefined,
  });
  return data;
}

/**
 * `POST /users/{id}/profiles/` — otorga/reactiva de forma idempotente el acceso a una o varias
 * entidades bajo un rol. Devuelve la lista de perfiles resultante.
 */
export async function assignUserProfiles(
  userId: number,
  payload: AssignProfilesPayload,
): Promise<UserProfileRead[]> {
  const { data } = await api.post<UserProfileRead[]>(`/users/${userId}/profiles/`, payload);
  return data;
}

/** `DELETE /users/{id}/profiles/?profile_id=` — baja lógica de un perfil concreto. */
export async function revokeUserProfile(userId: number, profileId: number): Promise<void> {
  await api.delete(`/users/${userId}/profiles/`, { params: { profile_id: profileId } });
}

/** `GET /profile-entity-types/` — tipos de entidad asignables (para poblar el selector). */
export async function listAssignableEntityTypes(): Promise<AssignableEntityType[]> {
  const { data } = await api.get<AssignableEntityType[]>("/profile-entity-types/");
  return data;
}
