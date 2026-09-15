import { api } from "@/lib/api/client";
import type { AuthUser } from "@/lib/auth/store";

// ─── Tipos 2FA ────────────────────────────────────────────────────────────────

/** Respuesta de `POST /auth/2fa/setup/totp/`. */
export interface TotpSetupResponse {
  otpauth_uri: string;
  secret: string;
}

/** Body de `POST /auth/2fa/confirm-totp/`. */
export interface TotpConfirmPayload {
  otp_code: string;
}

/** Body de `POST /auth/2fa/setup/email/`. */
export interface EmailSetupPayload {
  password: string;
}

/**
 * Body de `DELETE /auth/2fa/disable/`.
 * Primera llamada EMAIL: `otp_code: ""` → backend envía OTP por correo.
 * Segunda llamada EMAIL / llamada TOTP: `otp_code` real → desactiva 2FA.
 */
export interface DisablePayload {
  password: string;
  otp_code: string;
}

/** Respuesta genérica de éxito del backend (mensaje textual). */
export interface TwoFactorMessageResponse {
  detalle: string;
}

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

// ─── API Reset de contraseña ─────────────────────────────────────────────────

export interface PasswordResetRequestPayload {
  username: string;
}

export interface PasswordResetConfirmPayload {
  username: string;
  otp_code: string;
  password_nueva: string;
}

/** Solicita el OTP de reset. Siempre 200 (no revela si el usuario existe). `POST /auth/password-reset/request/` */
export async function requestPasswordReset(payload: PasswordResetRequestPayload): Promise<void> {
  await api.post("/auth/password-reset/request/", payload);
}

/** Confirma el OTP y establece la nueva contraseña. `POST /auth/password-reset/confirm/` */
export async function confirmPasswordReset(payload: PasswordResetConfirmPayload): Promise<void> {
  await api.post("/auth/password-reset/confirm/", payload);
}

// ─── API 2FA ──────────────────────────────────────────────────────────────────

/**
 * Inicia el setup TOTP. Devuelve `{otpauth_uri, secret}` para generar el QR.
 * `POST /auth/2fa/setup/totp/`
 */
export async function setupTotp(): Promise<TotpSetupResponse> {
  const { data } = await api.post<TotpSetupResponse>("/auth/2fa/setup/totp/");
  return data;
}

/**
 * Confirma el código TOTP para activar 2FA. `POST /auth/2fa/confirm-totp/`
 */
export async function confirmTotp(payload: TotpConfirmPayload): Promise<TwoFactorMessageResponse> {
  const { data } = await api.post<TwoFactorMessageResponse>("/auth/2fa/confirm-totp/", payload);
  return data;
}

/**
 * Activa 2FA por correo electrónico. `POST /auth/2fa/setup/email/`
 */
export async function setupEmail2fa(payload: EmailSetupPayload): Promise<TwoFactorMessageResponse> {
  const { data } = await api.post<TwoFactorMessageResponse>("/auth/2fa/setup/email/", payload);
  return data;
}

/**
 * Desactiva 2FA. `DELETE /auth/2fa/disable/`
 * - Primera llamada EMAIL (otp_code: ""): backend envía OTP por correo → 200 + mensaje de envío.
 * - Segunda llamada EMAIL / llamada TOTP (otp_code real): desactiva → 200 "desactivado".
 */
export async function disable2fa(payload: DisablePayload): Promise<TwoFactorMessageResponse> {
  const { data } = await api.delete<TwoFactorMessageResponse>("/auth/2fa/disable/", {
    data: payload,
  });
  return data;
}
