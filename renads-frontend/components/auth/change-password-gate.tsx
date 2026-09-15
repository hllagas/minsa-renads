"use client";

import { useState } from "react";
import { toast } from "sonner";
import { EyeIcon, EyeOffIcon } from "lucide-react";

import { useAuthStore } from "@/lib/auth/store";
import { useChangePassword } from "@/lib/auth/hooks";
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

/**
 * Gate bloqueante de contraseña temporal (RN-22, Feature F3). Cuando el usuario tiene
 * `debe_cambiar_password`, muestra un diálogo **no cerrable** (sin botón X, `open` controlado sin
 * setter) que exige cambiar la clave antes de seguir. Al éxito el flag se limpia y desaparece.
 * El bloqueo real de endpoints lo hace el backend; esto es refuerzo del front.
 */
export function ChangePasswordGate() {
  const user = useAuthStore((s) => s.user);
  const changeM = useChangePassword();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirma, setConfirma] = useState("");
  const [showActual, setShowActual] = useState(false);
  const [showNueva, setShowNueva] = useState(false);
  const [showConfirma, setShowConfirma] = useState(false);

  if (!user?.debe_cambiar_password) return null;

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (nueva.length < 8) {
      toast.error("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (nueva !== confirma) {
      toast.error("La confirmación no coincide con la nueva contraseña.");
      return;
    }
    changeM.mutate(
      { password_actual: actual, password_nueva: nueva },
      {
        onSuccess: () => toast.success("Contraseña actualizada."),
        onError: (err) => toast.error(extractApiError(err)),
      },
    );
  }

  return (
    <Dialog open={true}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Cambia tu contraseña</DialogTitle>
          <DialogDescription>
            Tu cuenta usa una contraseña temporal. Debes cambiarla antes de continuar.
          </DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={onSubmit}>
          <div className="grid gap-2">
            <Label htmlFor="pwd-actual">Contraseña actual (temporal)</Label>
            <div className="relative">
              <Input
                id="pwd-actual"
                type={showActual ? "text" : "password"}
                autoComplete="current-password"
                value={actual}
                onChange={(e) => setActual(e.target.value)}
                required
                disabled={changeM.isPending}
                className="pr-10"
              />
              <button
                type="button"
                aria-label={showActual ? "Ocultar contraseña" : "Mostrar contraseña"}
                aria-pressed={showActual}
                className="absolute top-1/2 right-2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => setShowActual((v) => !v)}
              >
                {showActual ? <EyeOffIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="pwd-nueva">Nueva contraseña</Label>
            <div className="relative">
              <Input
                id="pwd-nueva"
                type={showNueva ? "text" : "password"}
                autoComplete="new-password"
                value={nueva}
                onChange={(e) => setNueva(e.target.value)}
                required
                disabled={changeM.isPending}
                className="pr-10"
              />
              <button
                type="button"
                aria-label={showNueva ? "Ocultar contraseña" : "Mostrar contraseña"}
                aria-pressed={showNueva}
                className="absolute top-1/2 right-2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => setShowNueva((v) => !v)}
              >
                {showNueva ? <EyeOffIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="pwd-confirma">Confirmar nueva contraseña</Label>
            <div className="relative">
              <Input
                id="pwd-confirma"
                type={showConfirma ? "text" : "password"}
                autoComplete="new-password"
                value={confirma}
                onChange={(e) => setConfirma(e.target.value)}
                required
                disabled={changeM.isPending}
                className="pr-10"
              />
              <button
                type="button"
                aria-label={showConfirma ? "Ocultar contraseña" : "Mostrar contraseña"}
                aria-pressed={showConfirma}
                className="absolute top-1/2 right-2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => setShowConfirma((v) => !v)}
              >
                {showConfirma ? <EyeOffIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <DialogFooter>
            <Button type="submit" disabled={changeM.isPending}>
              {changeM.isPending ? "Guardando…" : "Cambiar contraseña"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
