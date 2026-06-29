import { api } from "@/lib/api/client";
import type { SetPasswordPayload } from "@/lib/usuarios/types";

/**
 * Acción de cambio de contraseña de un usuario (`POST /users/{id}/set-password/`). Axios vive
 * únicamente en `lib/api/`. La contraseña es write-only: no se devuelve, no se cachea, no se loguea.
 */
export async function setUserPassword(id: number, password: string): Promise<void> {
  const payload: SetPasswordPayload = { password };
  await api.post(`/users/${id}/set-password/`, payload);
}
