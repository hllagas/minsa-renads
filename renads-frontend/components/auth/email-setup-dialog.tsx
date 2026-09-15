"use client";

import { useState } from "react";
import { toast } from "sonner";

import { useSetupEmail2fa } from "@/lib/auth/two-factor";
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

interface EmailSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Correo del usuario autenticado. */
  userEmail: string;
}

/**
 * Diálogo para activar 2FA por correo electrónico.
 * Solicita la contraseña actual y llama a `POST /auth/2fa/setup/email/`.
 */
export function EmailSetupDialog({ open, onOpenChange, userEmail }: EmailSetupDialogProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const setupM = useSetupEmail2fa();

  function handleClose(value: boolean) {
    if (!value) {
      setPassword("");
      setError("");
    }
    onOpenChange(value);
  }

  function handleActivar() {
    setError("");
    setupM.mutate(
      { password },
      {
        onSuccess: () => {
          toast.success("Autenticación por correo electrónico activada correctamente.");
          handleClose(false);
        },
        onError: (err) => {
          setError(extractApiError(err));
        },
      },
    );
  }

  const sinCorreo = !userEmail;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Activar 2FA por correo electrónico</DialogTitle>
          <DialogDescription>
            Se enviará un código de verificación a tu correo cada vez que inicies sesión.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          {sinCorreo ? (
            <p className="text-sm text-muted-foreground rounded border border-yellow-200 bg-yellow-50 px-3 py-2 dark:border-yellow-800 dark:bg-yellow-900/20">
              Tu cuenta no tiene correo registrado. Contacta al administrador para asignarlo.
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Se usará el correo{" "}
              <span className="font-medium text-foreground">{userEmail}</span>{" "}
              para enviar códigos de verificación.
            </p>
          )}

          <div className="grid gap-2">
            <Label htmlFor="email2fa-password">Contraseña actual</Label>
            <Input
              id="email2fa-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={setupM.isPending || sinCorreo}
              placeholder="Ingresa tu contraseña actual"
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => handleClose(false)}
            disabled={setupM.isPending}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleActivar}
            disabled={setupM.isPending || sinCorreo || !password}
          >
            {setupM.isPending ? "Activando…" : "Activar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
