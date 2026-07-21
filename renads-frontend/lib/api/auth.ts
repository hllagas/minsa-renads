import { api } from "@/lib/api/client";
import type { AuthUser } from "@/lib/auth/store";

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
  /** Flag de contraseña temporal (RN-22): true = el usuario debe cambiarla. */
  debe_cambiar_password?: boolean;
}

/** Obtiene el par de tokens JWT. `POST /auth/token/` (ver docs/api-auth.md). */
export async function login(credentials: LoginCredentials): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>("/auth/token/", credentials);
  return data;
}

/** Identidad, roles y perfiles del usuario autenticado. `GET /auth/me/`. */
export async function fetchMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>("/auth/me/");
  return data;
}

/** Cuerpo del cambio de la propia contraseña (`POST /auth/me/cambiar-password/`). */
export interface ChangePasswordPayload {
  password_actual: string;
  password_nueva: string;
}

/**
 * Cambia la propia contraseña y limpia `debe_cambiar_password` (RN-22).
 * Responde con el payload de `/auth/me/` (ya con el flag en `false`).
 */
export async function changePassword(payload: ChangePasswordPayload): Promise<AuthUser> {
  const { data } = await api.post<AuthUser>("/auth/me/cambiar-password/", payload);
  return data;
}
