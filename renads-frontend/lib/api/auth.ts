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

export interface TwoFactorPending {
  requires_2fa: true;
  session_token: string;
  method: "TOTP" | "EMAIL";
}

export type LoginResponse = TokenPair | TwoFactorPending;

export function isTwoFactorPending(res: LoginResponse): res is TwoFactorPending {
  return (res as TwoFactorPending).requires_2fa === true;
}

/** Obtiene el par de tokens JWT o la respuesta 2FA pendiente. `POST /auth/token/` */
export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/auth/token/", credentials);
  return data;
}

export interface TwoFactorVerifyPayload {
  session_token: string;
  otp_code: string;
}

/** Intercambia el session_token + OTP por el par JWT completo. `POST /auth/2fa/verify/` */
export async function verify2fa(payload: TwoFactorVerifyPayload): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>("/auth/2fa/verify/", payload);
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
