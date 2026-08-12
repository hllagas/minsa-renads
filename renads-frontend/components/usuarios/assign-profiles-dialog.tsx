"use client";

import { useState } from "react";
import { toast } from "sonner";

import type { User } from "@/lib/usuarios/types";
import {
  useAssignUserProfiles,
  useAssignableEntityTypes,
  useRevokeUserProfile,
  useUserProfiles,
} from "@/lib/usuarios/hooks";
import { ENTITY_ENDPOINTS } from "@/lib/usuarios/entity-endpoints";
import { extractApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { MultiEntityCombobox } from "@/components/form/multi-entity-combobox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Diálogo «Asignar entidades»: gestiona el alcance por objeto (`UserEntityProfile`) de un usuario.
 * Muestra el alcance actual (con revocación por baja lógica) y un formulario para otorgar acceso a
 * una o varias entidades de un tipo bajo un rol, vía `POST /users/{id}/profiles/` (idempotente).
 * Solo lo monta la página de cuentas, que ya está gateada a superusuario (backend: `IsSuperUser`).
 */
export function AssignProfilesDialog({
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
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Asignar entidades</DialogTitle>
          <DialogDescription>
            {user ? `Alcance institucional de: ${user.username}` : null}
          </DialogDescription>
        </DialogHeader>
        {user ? <AssignProfilesBody key={user.id} userId={user.id} /> : null}
      </DialogContent>
    </Dialog>
  );
}

function AssignProfilesBody({ userId }: { userId: number }) {
  const profiles = useUserProfiles(userId);
  const types = useAssignableEntityTypes();
  const assignM = useAssignUserProfiles(userId);
  const revokeM = useRevokeUserProfile(userId);

  const [rol, setRol] = useState<number | null>(null);
  const [tipoEntidad, setTipoEntidad] = useState<string | null>(null);
  const [ids, setIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);

  const mapping = tipoEntidad ? ENTITY_ENDPOINTS[tipoEntidad] : undefined;

  function onAssign(e: React.FormEvent) {
    e.preventDefault();
    if (rol == null) {
      setError("El rol es obligatorio.");
      return;
    }
    if (!tipoEntidad) {
      setError("El tipo de entidad es obligatorio.");
      return;
    }
    if (ids.length === 0) {
      setError("Selecciona al menos una entidad.");
      return;
    }
    setError(null);
    assignM.mutate(
      { rol, tipo_entidad: tipoEntidad, ids },
      {
        onSuccess: () => {
          toast.success("Alcance asignado.");
          setIds([]);
        },
        onError: (err) => setError(extractApiError(err)),
      },
    );
  }

  function onRevoke(profileId: number) {
    if (confirmingId !== profileId) {
      setConfirmingId(profileId);
      return;
    }
    revokeM.mutate(profileId, {
      onSuccess: () => {
        toast.success("Acceso revocado.");
        setConfirmingId(null);
      },
      onError: (err) => {
        toast.error(extractApiError(err));
        setConfirmingId(null);
      },
    });
  }

  const items = types.data ?? [];
  const activos = (profiles.data ?? []).filter((p) => p.activo);

  return (
    <div className="grid gap-5">
      {/* Alcance actual */}
      <section className="grid gap-2">
        <h3 className="text-sm font-medium">Alcance actual</h3>
        {profiles.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando…</p>
        ) : activos.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            El usuario no tiene entidades asignadas.
          </p>
        ) : (
          <ul className="grid gap-1.5">
            {activos.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between gap-2 rounded-md border p-2 text-sm"
              >
                <span className="min-w-0">
                  <span className="truncate font-medium">{p.entidad}</span>{" "}
                  <Badge variant="secondary">{p.rol}</Badge>
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant={confirmingId === p.id ? "destructive" : "outline"}
                  onClick={() => onRevoke(p.id)}
                  disabled={revokeM.isPending}
                >
                  {confirmingId === p.id ? "Confirmar" : "Revocar"}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Asignar nuevo alcance */}
      <form onSubmit={onAssign} className="grid gap-4 border-t pt-4">
        <h3 className="text-sm font-medium">Asignar</h3>

        <div className="grid gap-1.5">
          <Label>Rol *</Label>
          <EntityCombobox
            endpoint="groups"
            value={rol}
            onChange={setRol}
            toLabel={(r) => String(r.name ?? r.id)}
            placeholder="Buscar rol…"
          />
        </div>

        <div className="grid gap-1.5">
          <Label>Tipo de entidad *</Label>
          <Select
            items={items.map((t) => ({ value: t.tipo_entidad, label: t.label }))}
            value={tipoEntidad}
            onValueChange={(v: string | null) => {
              setTipoEntidad(v);
              setIds([]); // las entidades dependen del tipo
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccionar tipo…" />
            </SelectTrigger>
            <SelectContent>
              {items.map((t) => (
                <SelectItem key={t.tipo_entidad} value={t.tipo_entidad}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-1.5">
          <Label>Entidades *</Label>
          {mapping ? (
            <MultiEntityCombobox
              key={mapping.endpoint}
              endpoint={mapping.endpoint}
              value={ids}
              onChange={setIds}
              toLabel={mapping.toLabel}
              placeholder="Buscar entidad…"
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              Elige primero el tipo de entidad.
            </p>
          )}
        </div>

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <DialogFooter>
          <Button type="submit" disabled={assignM.isPending}>
            {assignM.isPending ? "Asignando…" : "Asignar"}
          </Button>
        </DialogFooter>
      </form>
    </div>
  );
}
