"use client";

import { useState } from "react";
import { toast } from "sonner";

import { useDisable2fa } from "@/lib/auth/two-factor";
import { extractApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface TwoFactorDisableDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Método 2FA activo del usuario. */
  method: "TOTP" | "EMAIL";
}

type DisableStep = "credentials" | "otp_pending";

/**
 * Diálogo para desactivar 2FA.
 * - TOTP: campo contraseña + campo OTP en un solo paso.
 * - EMAIL: paso 1 solo contraseña (envía OTP al correo), paso 2 ingresa el OTP recibido.
 */
export function TwoFactorDisableDialog({
  open,
  onOpenChange,
  method,
}: TwoFactorDisableDialogProps) {
  const [step, setStep] = useState<DisableStep>("credentials");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [error, setError] = useState("");

  const disableM = useDisable2fa();

  function resetState() {
    setStep("credentials");
    setPassword("");
    setOtpCode("");
    setError("");
  }

  function handleClose(value: boolean) {
    if (!value) resetState();
    onOpenChange(value);
  }

  // TOTP: envía contraseña + OTP juntos en un solo paso
  function handleDisableTotp() {
    setError("");
    disableM.mutate(
      { password, otp_code: otpCode },
      {
        onSuccess: () => {
          toast.success("Doble factor desactivado.");
          handleClose(false);
        },
        onError: (err) => {
          setError(extractApiError(err));
        },
      },
    );
  }

  // EMAIL Paso 1: envía contraseña con otp_code vacío para que el backend envíe el OTP al correo
  function handleSendOtp() {
    setError("");
    disableM.mutate(
      { password, otp_code: "" },
      {
        onSuccess: () => {
          // La mutación tuvo éxito → el OTP fue enviado → avanzar al paso 2
          setStep("otp_pending");
        },
        onError: (err) => {
          setError(extractApiError(err));
        },
      },
    );
  }

  // EMAIL Paso 2: envía contraseña + OTP recibido para desactivar
  function handleDisableEmail() {
    setError("");
    disableM.mutate(
      { password, otp_code: otpCode },
      {
        onSuccess: () => {
          toast.success("Doble factor desactivado.");
          handleClose(false);
        },
        onError: (err) => {
          setError(extractApiError(err));
        },
      },
    );
  }

  const methodLabel = method === "TOTP" ? "app autenticadora" : "correo electrónico";

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Desactivar 2FA</DialogTitle>
          <DialogDescription>
            {method === "TOTP"
              ? "Ingresa tu contraseña y el código de tu app autenticadora para desactivar el segundo factor."
              : step === "credentials"
              ? "Ingresa tu contraseña para recibir un código de verificación en tu correo."
              : "Ingresa el código enviado a tu correo para confirmar la desactivación."}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          {/* Contraseña — siempre visible */}
          <div className="grid gap-2">
            <Label htmlFor="disable2fa-password">Contraseña actual</Label>
            <Input
              id="disable2fa-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={disableM.isPending || step === "otp_pending"}
              placeholder="Ingresa tu contraseña actual"
            />
          </div>

          {/* OTP — visible para TOTP siempre, y para EMAIL en paso 2 */}
          {(method === "TOTP" || step === "otp_pending") && (
            <div className="grid gap-2">
              <Label htmlFor="disable2fa-otp">
                {method === "TOTP"
                  ? "Código de tu app autenticadora"
                  : "Código recibido en tu correo"}
              </Label>
              <Input
                id="disable2fa-otp"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="123456"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                disabled={disableM.isPending}
                autoComplete="one-time-code"
              />
              {step === "otp_pending" && (
                <p className="text-xs text-muted-foreground">
                  Introduce el código enviado a tu correo electrónico (método {methodLabel}).
                </p>
              )}
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => handleClose(false)}
            disabled={disableM.isPending}
          >
            Cancelar
          </Button>

          {/* TOTP: botón único para desactivar */}
          {method === "TOTP" && (
            <Button
              type="button"
              variant="destructive"
              onClick={handleDisableTotp}
              disabled={disableM.isPending || !password || otpCode.length < 6}
            >
              {disableM.isPending ? "Desactivando…" : "Desactivar"}
            </Button>
          )}

          {/* EMAIL Paso 1: enviar código */}
          {method === "EMAIL" && step === "credentials" && (
            <Button
              type="button"
              onClick={handleSendOtp}
              disabled={disableM.isPending || !password}
            >
              {disableM.isPending ? "Enviando…" : "Enviar código"}
            </Button>
          )}

          {/* EMAIL Paso 2: desactivar con OTP */}
          {method === "EMAIL" && step === "otp_pending" && (
            <Button
              type="button"
              variant="destructive"
              onClick={handleDisableEmail}
              disabled={disableM.isPending || otpCode.length < 6}
            >
              {disableM.isPending ? "Desactivando…" : "Desactivar"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
