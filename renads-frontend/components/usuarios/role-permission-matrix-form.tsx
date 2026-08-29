"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Search } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Group } from "@/lib/usuarios/types";
import {
  ACTION_LABELS,
  PERMISSION_ACTIONS,
  buildPermissionMatrix,
  useAllPermissions,
  type AppPermissions,
  type PermissionAction,
} from "@/lib/usuarios/permissions-matrix";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/** Estado tri de una columna a nivel de aplicación: todos / algunos / ninguno marcados. */
type TriState = "all" | "some" | "none";

/**
 * Formulario integrado de un rol (`groups`): nombre + matriz compacta de permisos por
 * Aplicación → Modelo → acciones (add/change/delete/view). Reemplaza el multiselect plano.
 *
 * Los permisos personalizados (no estándar) del rol se conservan tal cual: `selected` se
 * inicializa con TODOS los permisos actuales y la matriz solo alterna los ids estándar.
 */
export function RolePermissionMatrixForm({
  initial,
  submitting,
  onSubmit,
  onCancel,
}: {
  initial: Group | null;
  submitting?: boolean;
  onSubmit: (payload: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const permsQuery = useAllPermissions();
  const matrix = useMemo(
    () => buildPermissionMatrix(permsQuery.data ?? []),
    [permsQuery.data],
  );

  const [name, setName] = useState(initial?.name ?? "");
  const [nameError, setNameError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(initial?.permissions ?? []),
  );
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(initial?.permissions_detalle?.map((p) => p.app_label) ?? []),
  );

  const searchLower = search.trim().toLowerCase();

  // Apps/modelos filtrados por la búsqueda (por etiqueta de app o de modelo).
  const visibleApps = useMemo<AppPermissions[]>(() => {
    if (!searchLower) return matrix.apps;
    return matrix.apps
      .map((app) => {
        const appMatches = app.label.toLowerCase().includes(searchLower);
        const models = appMatches
          ? app.models
          : app.models.filter((m) => m.label.toLowerCase().includes(searchLower));
        return { ...app, models };
      })
      .filter((app) => app.models.length > 0);
  }, [matrix.apps, searchLower]);

  const allExpanded =
    visibleApps.length > 0 && visibleApps.every((a) => expanded.has(a.app));

  function toggleExpanded(app: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(app)) next.delete(app);
      else next.add(app);
      return next;
    });
  }

  function toggleAllExpanded() {
    setExpanded(allExpanded ? new Set() : new Set(matrix.apps.map((a) => a.app)));
  }

  function togglePerm(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  /** ids de permiso de una columna (acción) dentro de una app. */
  function columnIds(app: AppPermissions, action: PermissionAction): number[] {
    const ids: number[] = [];
    for (const m of app.models) {
      const id = m.actions[action];
      if (id != null) ids.push(id);
    }
    return ids;
  }

  function columnState(app: AppPermissions, action: PermissionAction): TriState {
    const ids = columnIds(app, action);
    if (ids.length === 0) return "none";
    const on = ids.filter((id) => selected.has(id)).length;
    if (on === 0) return "none";
    if (on === ids.length) return "all";
    return "some";
  }

  /** N.º de permisos estándar marcados dentro de una app (badge de la fila). */
  function appSelectedCount(app: AppPermissions): number {
    let n = 0;
    for (const m of app.models)
      for (const action of PERMISSION_ACTIONS) {
        const id = m.actions[action];
        if (id != null && selected.has(id)) n += 1;
      }
    return n;
  }

  /** Marca/desmarca toda una columna (acción) de una app. */
  function toggleColumn(app: AppPermissions, action: PermissionAction) {
    const ids = columnIds(app, action);
    if (ids.length === 0) return;
    const allOn = ids.every((id) => selected.has(id));
    setSelected((prev) => {
      const next = new Set(prev);
      for (const id of ids) {
        if (allOn) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  }

  function handleSubmit() {
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("El nombre del rol es obligatorio.");
      return;
    }
    onSubmit({ name: trimmed, permissions: Array.from(selected) });
  }

  const selectedManagedCount = useMemo(() => {
    let n = 0;
    for (const id of selected) if (matrix.managedIds.has(id)) n += 1;
    return n;
  }, [selected, matrix.managedIds]);

  return (
    <div className="flex max-h-[72vh] flex-col gap-3">
      {/* Barra: nombre + búsqueda en una sola fila */}
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="grid gap-1">
          <Label htmlFor="role-name" className="text-xs text-muted-foreground">
            Nombre del rol *
          </Label>
          <Input
            id="role-name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (nameError) setNameError(null);
            }}
            placeholder="p. ej. DIGEP"
            aria-invalid={!!nameError}
          />
          {nameError ? (
            <p className="text-xs text-destructive">{nameError}</p>
          ) : null}
        </div>
        <div className="grid gap-1">
          <Label htmlFor="perm-search" className="text-xs text-muted-foreground">
            Filtrar permisos
          </Label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="perm-search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Aplicación o modelo…"
              className="pl-8"
            />
          </div>
        </div>
      </div>

      {/* Acciones de la matriz: expandir/contraer + contador */}
      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={toggleAllExpanded}
          disabled={visibleApps.length === 0}
        >
          {allExpanded ? "Contraer todo" : "Expandir todo"}
        </Button>
        <span className="text-xs text-muted-foreground tabular-nums">
          {selectedManagedCount} permiso(s) seleccionado(s)
        </span>
      </div>

      {/* Matriz de permisos */}
      <div className="min-h-0 flex-1 overflow-auto rounded-md border">
        {permsQuery.isLoading ? (
          <p className="p-6 text-center text-sm text-muted-foreground">
            Cargando permisos…
          </p>
        ) : permsQuery.isError ? (
          <div className="flex flex-col items-center gap-3 p-6">
            <p className="text-sm text-destructive">
              No se pudieron cargar los permisos.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => permsQuery.refetch()}
              disabled={permsQuery.isFetching}
            >
              Reintentar
            </Button>
          </div>
        ) : visibleApps.length === 0 ? (
          <p className="p-6 text-center text-sm text-muted-foreground">
            Sin resultados para «{search}».
          </p>
        ) : (
          <Table className="text-sm">
            <TableHeader className="sticky top-0 z-10 bg-muted">
              <TableRow className="hover:bg-transparent">
                <TableHead className="h-9 min-w-[220px]">Aplicación / Modelo</TableHead>
                {PERMISSION_ACTIONS.map((action) => (
                  <TableHead key={action} className="h-9 w-[84px] text-center text-xs">
                    {ACTION_LABELS[action]}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleApps.map((app) => {
                const isOpen = expanded.has(app.app) || !!searchLower;
                return (
                  <AppRows
                    key={app.app}
                    app={app}
                    isOpen={isOpen}
                    count={appSelectedCount(app)}
                    onToggleExpand={() => toggleExpanded(app.app)}
                    selected={selected}
                    onTogglePerm={togglePerm}
                    columnState={columnState}
                    onToggleColumn={toggleColumn}
                  />
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Pie: acciones */}
      <div className="flex justify-end gap-2 border-t pt-3">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancelar
        </Button>
        <Button type="button" onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Guardando…" : "Guardar"}
        </Button>
      </div>
    </div>
  );
}

/** Celda de checkbox compacta con área de clic ampliada a toda la celda. */
function CheckCell({
  checked,
  indeterminate,
  ariaLabel,
  onToggle,
  empty,
}: {
  checked?: boolean;
  indeterminate?: boolean;
  ariaLabel: string;
  onToggle?: () => void;
  empty?: boolean;
}) {
  if (empty) {
    return (
      <TableCell className="py-1 text-center text-muted-foreground/50">·</TableCell>
    );
  }
  return (
    <TableCell className="p-0 text-center">
      <button
        type="button"
        aria-label={ariaLabel}
        onClick={onToggle}
        className="flex h-9 w-full items-center justify-center outline-none focus-visible:bg-accent"
      >
        <Checkbox
          checked={checked}
          indeterminate={indeterminate}
          className="pointer-events-none size-4"
          tabIndex={-1}
        />
      </button>
    </TableCell>
  );
}

/** Fila de cabecera de una aplicación + (si expandida) las filas de sus modelos. */
function AppRows({
  app,
  isOpen,
  count,
  onToggleExpand,
  selected,
  onTogglePerm,
  columnState,
  onToggleColumn,
}: {
  app: AppPermissions;
  isOpen: boolean;
  count: number;
  onToggleExpand: () => void;
  selected: Set<number>;
  onTogglePerm: (id: number) => void;
  columnState: (app: AppPermissions, action: PermissionAction) => TriState;
  onToggleColumn: (app: AppPermissions, action: PermissionAction) => void;
}) {
  return (
    <>
      <TableRow className="border-b bg-muted/30 hover:bg-muted/50">
        <TableCell className="py-1.5">
          <button
            type="button"
            onClick={onToggleExpand}
            className="flex w-full items-center gap-1.5 text-left font-medium outline-none"
            aria-expanded={isOpen}
          >
            {isOpen ? (
              <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
            )}
            <span className="truncate">{app.label}</span>
            {count > 0 ? (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-[11px] tabular-nums">
                {count}
              </Badge>
            ) : null}
          </button>
        </TableCell>
        {PERMISSION_ACTIONS.map((action) => {
          const state = columnState(app, action);
          const hasAny = app.models.some((m) => m.actions[action] != null);
          return (
            <CheckCell
              key={action}
              empty={!hasAny}
              ariaLabel={`Marcar todo «${ACTION_LABELS[action]}» en ${app.label}`}
              checked={state === "all"}
              indeterminate={state === "some"}
              onToggle={() => onToggleColumn(app, action)}
            />
          );
        })}
      </TableRow>

      {isOpen
        ? app.models.map((model, i) => (
            <TableRow
              key={model.model}
              className={cn("border-0", i % 2 === 1 && "bg-muted/10")}
            >
              <TableCell className="py-1 pl-8">{model.label}</TableCell>
              {PERMISSION_ACTIONS.map((action) => {
                const id = model.actions[action];
                return (
                  <CheckCell
                    key={action}
                    empty={id == null}
                    ariaLabel={`${ACTION_LABELS[action]} ${model.label}`}
                    checked={id != null && selected.has(id)}
                    onToggle={id != null ? () => onTogglePerm(id) : undefined}
                  />
                );
              })}
            </TableRow>
          ))
        : null}
    </>
  );
}
