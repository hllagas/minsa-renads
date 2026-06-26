import { api } from "@/lib/api/client";
import type { AuthUser } from "@/lib/auth/store";

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
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
