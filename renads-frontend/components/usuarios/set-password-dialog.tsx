"use client";

import { useState } from "react";
import { toast } from "sonner";

import type { User } from "@/lib/usuarios/types";
import { useSetPassword } from "@/lib/usuarios/hooks";
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
 * Diálogo de cambio de contraseña (acción `set-password`). La contraseña es write-only: no se
 * muestra (campos `type=password`), no se loguea, no se cachea ni se persiste en estado de cliente.
 * La política de fortaleza la valida el backend (se muestra su error si la rechaza).
 */
export function SetPasswordDialog({
  user,
  onClose,
}: {
  user: User | null;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={user !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Cambiar contraseña</DialogTitle>
          <DialogDescription>
            {user ? `Usuario: ${user.username}` : null}
          </DialogDescription>
        </DialogHeader>
        {user ? (
          // `key` reinicia los campos al cambiar de usuario, sin efectos.
          <SetPasswordForm key={user.id} userId={user.id} onClose={onClose} />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function SetPasswordForm({
  userId,
  onClose,
}: {
  userId: number;
  onClose: () => void;
}) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const setPasswordM = useSetPassword();

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!password) {
      setError("La contraseña es obligatoria.");
      return;
    }
    if (password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setError(null);
    setPasswordM.mutate(
      { id: userId, password },
      {
        onSuccess: () => {
          toast.success("Contraseña actualizada.");
          onClose();
        },
        onError: (err) => setError(extractApiError(err)),
      },
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-4">
      <div className="grid gap-1.5">
        <Label htmlFor="set-password-new">Nueva contraseña *</Label>
        <Input
          id="set-password-new"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={!!error}
        />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="set-password-confirm">Confirmar contraseña *</Label>
        <Input
          id="set-password-confirm"
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          aria-invalid={!!error}
        />
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          onClick={onClose}
          disabled={setPasswordM.isPending}
        >
          Cancelar
        </Button>
        <Button type="submit" disabled={setPasswordM.isPending}>
          {setPasswordM.isPending ? "Guardando…" : "Guardar contraseña"}
        </Button>
      </DialogFooter>
    </form>
  );
}
