"use client";

import { useEffect, useState } from "react";
import QRCode from "react-qr-code";
import { toast } from "sonner";
import { CopyIcon } from "lucide-react";

import { useSetupTotp, useConfirmTotp } from "@/lib/auth/two-factor";
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

interface TotpSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type Step = "scan" | "confirm";

/**
 * Diálogo de activación TOTP en 2 pasos:
 *  1. "Escanear QR" — muestra el QR y el secreto manual.
 *  2. "Confirmar código" — el usuario ingresa el OTP de su app.
 */
export function TotpSetupDialog({ open, onOpenChange }: TotpSetupDialogProps) {
  const [step, setStep] = useState<Step>("scan");
  const [otpauthUri, setOtpauthUri] = useState("");
  const [secret, setSecret] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [error, setError] = useState("");

  const setupM = useSetupTotp();
  const confirmM = useConfirmTotp();

  // Al abrir, lanzar automáticamente el setup TOTP
  useEffect(() => {
    if (!open) return;
    setupM.mutate(undefined, {
      onSuccess: (data) => {
        setOtpauthUri(data.otpauth_uri);
        setSecret(data.secret);
      },
      onError: (err) => {
        setError(extractApiError(err));
      },
    });
    // setupM es estable — no necesita estar en deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function handleOpenChange(val: boolean) {
    if (val) {
      setStep("scan");
      setOtpCode("");
      setError("");
    }
    onOpenChange(val);
  }

  function handleCopySecret() {
    navigator.clipboard.writeText(secret).then(() => {
      toast.success("Clave secreta copiada al portapapeles.");
    });
  }

  function handleConfirm() {
    setError("");
    confirmM.mutate(
      { otp_code: otpCode },
      {
        onSuccess: () => {
          toast.success("Autenticación TOTP activada correctamente.");
          onOpenChange(false);
        },
        onError: (err) => {
          setError(extractApiError(err));
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Activar app autenticadora (TOTP)</DialogTitle>
          <DialogDescription>
            {step === "scan"
              ? "Escanea el código QR con tu app (Google Authenticator, Authy, etc.)."
              : "Introduce el código de 6 dígitos generado por tu app."}
          </DialogDescription>
        </DialogHeader>

        {step === "scan" && (
          <div className="flex flex-col items-center gap-4">
            {setupM.isPending && (
              <p className="text-sm text-muted-foreground">Generando código QR…</p>
            )}
            {!setupM.isPending && otpauthUri && (
              <>
                <div className="rounded border p-3 bg-white">
                  <QRCode value={otpauthUri} size={200} />
                </div>
                <div className="w-full grid gap-1">
                  <p className="text-xs text-muted-foreground">
                    ¿No puedes escanear? Ingresa esta clave manualmente:
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 rounded bg-muted px-2 py-1 text-xs font-mono break-all">
                      {secret}
                    </code>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={handleCopySecret}
                      aria-label="Copiar clave secreta"
                    >
                      <CopyIcon className="size-4" />
                    </Button>
                  </div>
                </div>
              </>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        )}

        {step === "confirm" && (
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="totp-otp-code">Código de verificación</Label>
              <Input
                id="totp-otp-code"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={6}
                placeholder="123456"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                disabled={confirmM.isPending}
                autoComplete="one-time-code"
              />
              <p className="text-xs text-muted-foreground">
                Introduce el código de 6 dígitos de tu app autenticadora.
              </p>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>
        )}

        <DialogFooter className="flex-col gap-2 sm:flex-row">
          {step === "scan" && (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                onClick={() => setStep("confirm")}
                disabled={setupM.isPending || !otpauthUri}
              >
                Continuar
              </Button>
            </>
          )}
          {step === "confirm" && (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep("scan")}
                disabled={confirmM.isPending}
              >
                Atrás
              </Button>
              <Button
                type="button"
                onClick={handleConfirm}
                disabled={confirmM.isPending || otpCode.length < 6}
              >
                {confirmM.isPending ? "Activando…" : "Activar"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
