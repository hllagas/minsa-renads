"use client";

import { SmartphoneIcon, MailIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface TwoFactorMethodSelectorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Correo del usuario; si está vacío, la opción EMAIL aparece deshabilitada. */
  userEmail: string;
  /** Callback al elegir método TOTP. */
  onSelectTotp: () => void;
  /** Callback al elegir método EMAIL. */
  onSelectEmail: () => void;
}

/**
 * Diálogo selector de método 2FA.
 * Muestra dos opciones: App autenticadora (TOTP) y Correo electrónico (EMAIL).
 * La opción EMAIL está deshabilitada si el usuario no tiene correo registrado.
 */
export function TwoFactorMethodSelector({
  open,
  onOpenChange,
  userEmail,
  onSelectTotp,
  onSelectEmail,
}: TwoFactorMethodSelectorProps) {
  const sinCorreo = !userEmail;

  function handleSelectTotp() {
    onOpenChange(false);
    onSelectTotp();
  }

  function handleSelectEmail() {
    if (sinCorreo) return;
    onOpenChange(false);
    onSelectEmail();
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Activar segundo factor de autenticación</DialogTitle>
          <DialogDescription>
            Elige el método que prefieres para proteger tu cuenta.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 py-2">
          {/* Opción TOTP */}
          <button
            type="button"
            onClick={handleSelectTotp}
            className="flex items-start gap-4 rounded-lg border p-4 text-left transition-colors hover:bg-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <SmartphoneIcon className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="text-sm font-medium leading-none">App autenticadora (TOTP)</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Usa Google Authenticator, Authy u otra app para generar códigos.
              </p>
            </div>
          </button>

          {/* Opción EMAIL */}
          <button
            type="button"
            onClick={handleSelectEmail}
            disabled={sinCorreo}
            title={sinCorreo ? "Sin correo registrado" : undefined}
            className="flex items-start gap-4 rounded-lg border p-4 text-left transition-colors hover:bg-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <MailIcon className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="text-sm font-medium leading-none">Correo electrónico</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {sinCorreo
                  ? "Sin correo registrado — contacta al administrador."
                  : `Recibirás un código en ${userEmail}.`}
              </p>
            </div>
          </button>
        </div>

        <div className="flex justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancelar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
