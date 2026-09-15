"use client";

import { useState } from "react";
import { toast } from "sonner";

import type { User, UserProfileRead } from "@/lib/usuarios/types";
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
      <DialogContent className="flex max-h-[90dvh] flex-col sm:max-w-2xl">
        <DialogHeader className="shrink-0">
          <DialogTitle>Asignar entidades</DialogTitle>
          <DialogDescription>
            {user ? `Alcance institucional de: ${user.username}` : null}
          </DialogDescription>
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          {user ? <AssignProfilesBody key={user.id} user={user} /> : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function AssignProfilesBody({ user }: { user: User }) {
  const userId = user.id;
  const profiles = useUserProfiles(userId);
  const types = useAssignableEntityTypes();
  const assignM = useAssignUserProfiles(userId);
  const revokeM = useRevokeUserProfile(userId);

  // Solo se puede asignar entidades bajo un rol que el usuario YA tiene (`groups_detalle`).
  const roles = user.groups_detalle ?? [];
  const hasRoles = roles.length > 0;

  // Un único rol → preseleccionado y fijo (no se pide elegir); varios → dropdown acotado.
  const [rol, setRol] = useState<number | null>(
    roles.length === 1 ? roles[0].id : null,
  );
  const [tipoEntidad, setTipoEntidad] = useState<string | null>(null);
  // PK de la entidad asignada: numérica o textual (ipress `codigo_renipress`, executing-units `codigo`).
  const [ids, setIds] = useState<(string | number)[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  // Perfil que se está editando: precarga sus valores en el formulario (rol/tipo/entidad).
  const [editingId, setEditingId] = useState<number | null>(null);
  // Datos originales del perfil en edición (rol/tipo/entidad). Si el guardado no los reproduce
  // exactamente, se considera un reemplazo y el perfil original se da de baja al guardar.
  const [editingOrig, setEditingOrig] = useState<{
    rolId: number | null;
    tipo: string;
    objId: string | number;
  } | null>(null);

  const mapping = tipoEntidad ? ENTITY_ENDPOINTS[tipoEntidad] : undefined;

  /** Rol por defecto del formulario (fijo si el usuario solo tiene uno). */
  const defaultRol = roles.length === 1 ? roles[0].id : null;

  /** Carga un perfil guardado en el formulario para revisarlo/editarlo. */
  function onEdit(p: UserProfileRead) {
    // `p.rol` es el nombre del grupo; se resuelve a su id contra los roles del usuario.
    const rolId = roles.find((r) => r.name === p.rol)?.id ?? defaultRol;
    setRol(rolId);
    setTipoEntidad(p.tipo_entidad);
    setIds([p.id_objeto]);
    setEditingId(p.id);
    setEditingOrig({ rolId, tipo: p.tipo_entidad, objId: p.id_objeto });
    setError(null);
  }

  /** Descarta la edición en curso y deja el formulario en su estado inicial. */
  function cancelEdit() {
    setEditingId(null);
    setEditingOrig(null);
    setRol(defaultRol);
    setTipoEntidad(null);
    setIds([]);
    setError(null);
  }

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
    // Al editar: si el guardado no reproduce EXACTO el perfil original (mismo rol + tipo + entidad),
    // se considera reemplazo y el original se da de baja tras crear el/los nuevo(s). Si es idéntico,
    // no se revoca (el POST idempotente reactiva la misma fila; revocarla la desactivaría).
    const originalId = editingId;
    const revocarOriginal =
      editingOrig != null &&
      originalId != null &&
      !(editingOrig.rolId === rol &&
        editingOrig.tipo === tipoEntidad &&
        ids.includes(editingOrig.objId));
    assignM.mutate(
      { rol, tipo_entidad: tipoEntidad, ids },
      {
        onSuccess: () => {
          if (revocarOriginal) revokeM.mutate(originalId);
          toast.success(editingId != null ? "Alcance actualizado." : "Alcance asignado.");
          setIds([]);
          setEditingId(null);
          setEditingOrig(null);
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
                className={`flex items-center justify-between gap-2 rounded-md border p-2 text-sm ${
                  editingId === p.id ? "border-primary bg-primary/5" : ""
                }`}
              >
                <span className="min-w-0">
                  <span className="truncate font-medium">{p.entidad}</span>{" "}
                  <Badge variant="secondary">{p.rol}</Badge>
                </span>
                <div className="flex shrink-0 items-center gap-1.5">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => onEdit(p)}
                    disabled={revokeM.isPending}
                  >
                    Editar
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant={confirmingId === p.id ? "destructive" : "outline"}
                    onClick={() => onRevoke(p.id)}
                    disabled={revokeM.isPending}
                  >
                    {confirmingId === p.id ? "Confirmar" : "Revocar"}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Asignar nuevo alcance */}
      <form onSubmit={onAssign} className="grid gap-4 border-t pt-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-medium">
            {editingId != null ? "Editar alcance" : "Asignar"}
          </h3>
          {editingId != null ? (
            <Button type="button" size="sm" variant="ghost" onClick={cancelEdit}>
              Cancelar edición
            </Button>
          ) : null}
        </div>

        {!hasRoles ? (
          <p className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
            El usuario no tiene ningún rol asignado. Asígnale primero un rol en su
            cuenta para poder acotar su alcance por entidad.
          </p>
        ) : null}

        <div className="grid gap-1.5">
          <Label>Rol *</Label>
          {roles.length === 1 ? (
            // Un solo rol: fijo (read-only), no se pide elegir.
            <div className="flex h-9 items-center rounded-md border bg-muted/40 px-3 text-sm">
              {roles[0].name}
            </div>
          ) : (
            <Select
              items={roles.map((r) => ({ value: String(r.id), label: r.name }))}
              value={rol != null ? String(rol) : null}
              onValueChange={(v: string | null) => setRol(v != null ? Number(v) : null)}
            >
              <SelectTrigger className="w-full" disabled={!hasRoles}>
                <SelectValue placeholder="Seleccionar rol…" />
              </SelectTrigger>
              <SelectContent>
                {roles.map((r) => (
                  <SelectItem key={r.id} value={String(r.id)}>
                    {r.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <p className="text-xs text-muted-foreground">
            Solo los roles que el usuario ya tiene.
          </p>
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
              valueKey={mapping.valueKey}
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

        <DialogFooter className="sticky bottom-0 pt-2">
          <Button type="submit" disabled={assignM.isPending || !hasRoles}>
            {assignM.isPending
              ? "Guardando…"
              : editingId != null
                ? "Guardar cambios"
                : "Asignar"}
          </Button>
        </DialogFooter>
      </form>
    </div>
  );
}
