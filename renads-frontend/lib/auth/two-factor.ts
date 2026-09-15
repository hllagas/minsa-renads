"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  confirmTotp,
  disable2fa,
  setupEmail2fa,
  setupTotp,
  type TotpConfirmPayload,
  type TotpSetupResponse,
  type DisablePayload,
  type EmailSetupPayload,
  type TwoFactorMessageResponse,
} from "@/lib/api/auth";
import { meQueryKey } from "@/lib/auth/hooks";

/**
 * Inicia el setup TOTP. Devuelve `{otpauth_uri, secret}` para renderizar el QR.
 * No invalida nada: el 2FA aún no está activo hasta confirmar.
 */
export function useSetupTotp() {
  return useMutation<TotpSetupResponse, Error, void>({
    mutationFn: () => setupTotp(),
  });
}

/**
 * Confirma el código TOTP para activar 2FA.
 * En éxito invalida `meQueryKey` para refrescar el estado 2FA en el widget.
 */
export function useConfirmTotp() {
  const qc = useQueryClient();
  return useMutation<TwoFactorMessageResponse, Error, TotpConfirmPayload>({
    mutationFn: (payload) => confirmTotp(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: meQueryKey });
    },
  });
}

/**
 * Activa 2FA por correo electrónico.
 * En éxito invalida `meQueryKey` para refrescar el estado 2FA en el widget.
 */
export function useSetupEmail2fa() {
  const qc = useQueryClient();
  return useMutation<TwoFactorMessageResponse, Error, EmailSetupPayload>({
    mutationFn: (payload) => setupEmail2fa(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: meQueryKey });
    },
  });
}

/**
 * Desactiva 2FA.
 * - Primera llamada EMAIL (`otp_code: ""`): backend envía OTP al correo → HTTP 200. El componente
 *   detecta que fue la llamada inicial (otp vacío) y muestra el campo OTP.
 * - Segunda llamada EMAIL / llamada TOTP: desactiva definitivamente → HTTP 200.
 * En éxito invalida `meQueryKey` para refrescar el estado 2FA en el widget.
 */
export function useDisable2fa() {
  const qc = useQueryClient();
  return useMutation<TwoFactorMessageResponse, Error, DisablePayload>({
    mutationFn: (payload) => disable2fa(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: meQueryKey });
    },
  });
}
