"use client";

import React, { useMemo, useState } from "react";
import { ChevronRight, ChevronDown, CheckCircle2, XCircle, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import type { WithId } from "@/lib/api/query";
import { createResourceHooks } from "@/lib/crud/hooks";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { extractApiError } from "@/lib/api/errors";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { clinicalFieldRegistrationsConfig } from "@/lib/convenios/clinical-fields";

import { PageHeader } from "@/components/data/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EntityCombobox } from "@/components/form/entity-combobox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResourceForm } from "@/components/crud/resource-form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ─── helpers ────────────────────────────────────────────────────────────────

function nestedNombre(v: unknown): string {
  if (!v) return "";
  if (typeof v === "object" && "nombre" in v) return String((v as Record<string, unknown>).nombre ?? "");
  return "";
}

function getAmbitoNombre(ip: WithId): string {
  return (
    nestedNombre(ip.ambito_geografico_sanitario) ||
    String(ip.ambito_geografico_sanitario_nombre ?? "") ||
    String(ip.ambito_nombre ?? "") ||
    "—"
  );
}

function getRedNombre(ip: WithId): string {
  return (
    nestedNombre(ip.red) ||
    String(ip.red_nombre ?? "") ||
    "—"
  );
}

function getAmbitoId(ip: WithId): number | null {
  const ags = ip.ambito_geografico_sanitario;
  if (!ags) return null;
  if (typeof ags === "number") return ags;
  if (typeof ags === "object" && "id" in ags) return (ags as { id: number }).id;
  return null;
}

const ESTADOS_VIGENTES = new Set([
  "VIGENTE",
  "PUBLICADO",
  "SUSCRITO",
  "FIRMADO_MINSA",
  "CAMPOS_CLINICOS_DEFINIDOS",
]);

function isConvenioVigente(row: WithId): boolean {
  const conv = row.convenio_detalle as WithId | undefined;
  if (!conv) return false;
  return ESTADOS_VIGENTES.has(String(conv.estado_codigo ?? ""));
}

function rowText(row: WithId): string {
  const ip = row.ipress_detalle as WithId;
  const cp = row.carrera_profesional_detalle as WithId;
  return [
    getAmbitoNombre(ip),
    getRedNombre(ip),
    String(ip?.nombre ?? ""),
    String(cp?.nombre ?? ""),
  ]
    .join(" ")
    .toLowerCase();
}

// ─── grouping ───────────────────────────────────────────────────────────────

type GroupMode = "none" | "ambito" | "red" | "sede";

interface GroupItem {
  key: string;
  label: string;
  rows: WithId[];
  sumRegistrados: number;
  sumAsignados: number;
  sumDisponibles: number;
  anyVigente: boolean;
}

function buildGroups(rows: WithId[], mode: GroupMode): GroupItem[] {
  const map = new Map<string, WithId[]>();
  for (const row of rows) {
    const ip = row.ipress_detalle as WithId;
    let key: string;
    if (mode === "ambito") key = getAmbitoNombre(ip);
    else if (mode === "red") key = getRedNombre(ip);
    else key = `${String(ip.id ?? row.ipress)}`;
    const arr = map.get(key) ?? [];
    arr.push(row);
    map.set(key, arr);
  }
  return Array.from(map.entries()).map(([key, groupRows]) => {
    const ip0 = groupRows[0]?.ipress_detalle as WithId | undefined;
    let label: string;
    if (mode === "sede") label = String(ip0?.nombre ?? key);
    else label = key;
    return {
      key,
      label,
      rows: groupRows,
      sumRegistrados: groupRows.reduce((s, r) => s + (Number(r.campos_clinicos_registrados) || 0), 0),
      sumAsignados: groupRows.reduce((s, r) => s + (Number(r.campos_clinicos_asignados) || 0), 0),
      sumDisponibles: groupRows.reduce((s, r) => s + (Number(r.disponibilidad) || 0), 0),
      anyVigente: groupRows.some(isConvenioVigente),
    };
  });
}

// ─── sub-components ─────────────────────────────────────────────────────────

function VigenteBadge({ vigente }: { vigente: boolean }) {
  return vigente ? (
    <Badge className="gap-1 bg-emerald-600 text-xs font-normal hover:bg-emerald-600">
      <CheckCircle2 className="size-3" />
      Vigente
    </Badge>
  ) : (
    <Badge variant="outline" className="gap-1 text-xs font-normal text-muted-foreground">
      <XCircle className="size-3" />
      Sin vigente
    </Badge>
  );
}

function Num({ n, ok, warn }: { n: number; ok?: boolean; warn?: boolean }) {
  const cls = ok ? "text-emerald-600" : warn ? "text-destructive" : "";
  return <span className={`tabular-nums font-medium ${cls}`}>{n}</span>;
}

function DataRow({
  row,
  canWrite,
  indent,
  onEdit,
  onDelete,
}: {
  row: WithId;
  canWrite: boolean;
  indent?: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const ip = (row.ipress_detalle ?? {}) as WithId;
  const cp = (row.carrera_profesional_detalle ?? {}) as WithId;
  const reg = Number(row.campos_clinicos_registrados) || 0;
  const asig = Number(row.campos_clinicos_asignados) || 0;
  const disp = Number(row.disponibilidad) || 0;

  return (
    <TableRow>
      <TableCell className={`text-sm ${indent ? "pl-9" : ""}`}>
        <span className="text-muted-foreground">{getAmbitoNombre(ip)}</span>
      </TableCell>
      <TableCell className="text-sm">
        <span className="text-muted-foreground">{getRedNombre(ip)}</span>
      </TableCell>
      <TableCell className="text-sm font-medium">{String(ip.nombre ?? "—")}</TableCell>
      <TableCell className="text-sm">{String(cp.nombre ?? "—")}</TableCell>
      <TableCell className="text-right">
        <Num n={reg} />
      </TableCell>
      <TableCell className="text-right">
        <Num n={asig} />
      </TableCell>
      <TableCell className="text-right">
        <Num n={disp} ok={disp > 0} warn={disp === 0} />
      </TableCell>
      <TableCell>
        <VigenteBadge vigente={isConvenioVigente(row)} />
      </TableCell>
      {canWrite ? (
        <TableCell>
          <div className="flex justify-end gap-1">
            <Button variant="outline" size="icon-sm" aria-label="Editar" title="Editar" onClick={onEdit}>
              <Pencil />
            </Button>
            <Button
              variant="destructive"
              size="icon-sm"
              aria-label="Eliminar"
              title="Eliminar"
              onClick={onDelete}
            >
              <Trash2 />
            </Button>
          </div>
        </TableCell>
      ) : null}
    </TableRow>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

const ipressLabel = (r: WithId) =>
  [r.codigo_renipress, r.nombre].filter(Boolean).join(" — ") || String(r.id);

export function DeterminacionView() {
  const user = useAuthStore((s) => s.user);
  const canWrite = userHasRole(user, "CONAPRES", "Administrador RENADS");

  // ── server-side filters
  const [filterIpress, setFilterIpress] = useState<number | null>(null);
  const [filterCarrera, setFilterCarrera] = useState<number | null>(null);

  // ── client-side filters
  const [filterAmbitoId, setFilterAmbitoId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  // ── grouping
  const [groupMode, setGroupMode] = useState<GroupMode>("none");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // ── CRUD state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<WithId | null>(null);
  const [deleting, setDeleting] = useState<WithId | null>(null);

  // ── data
  const hooks = useMemo(
    () => createResourceHooks<WithId, Record<string, unknown>>("clinical-field-registrations"),
    [],
  );

  const list = hooks.useList({
    ordering: "ipress__nombre,carrera_profesional__nombre",
    filters: {
      ...(filterIpress ? { ipress: filterIpress } : {}),
      ...(filterCarrera ? { carrera_profesional: filterCarrera } : {}),
      page_size: 500,
    },
  });

  const createM = hooks.useCreate();
  const updateM = hooks.useUpdate();
  const removeM = hooks.useRemove();

  // ── derived
  const allRows = useMemo<WithId[]>(() => {
    let rows = list.data?.results ?? [];
    if (filterAmbitoId) {
      rows = rows.filter(
        (r) => getAmbitoId((r.ipress_detalle ?? {}) as WithId) === filterAmbitoId,
      );
    }
    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase();
      rows = rows.filter((r) => rowText(r).includes(q));
    }
    return rows;
  }, [list.data, filterAmbitoId, debouncedSearch]);

  const groups = useMemo(
    () => (groupMode !== "none" ? buildGroups(allRows, groupMode) : []),
    [allRows, groupMode],
  );

  function toggleExpand(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function onSubmit(payload: Record<string, unknown>) {
    const opts = {
      onSuccess: () => {
        toast.success(editing ? "Cambios guardados." : "Registro creado.");
        setDialogOpen(false);
        setEditing(null);
      },
      onError: (e: unknown) => toast.error(extractApiError(e)),
    };
    if (editing) updateM.mutate({ id: editing.id, payload }, opts);
    else createM.mutate(payload, opts);
  }

  function confirmDelete() {
    if (!deleting) return;
    removeM.mutate(deleting.id, {
      onSuccess: () => {
        toast.success("Registro eliminado.");
        setDeleting(null);
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  const hasFilters = !!(filterAmbitoId || filterIpress || filterCarrera || search);
  const colCount = canWrite ? 9 : 8;

  // Build flat list of table rows for the grouped view
  const groupedTableRows: React.ReactNode[] = useMemo(() => {
    if (groupMode === "none") return [];
    const nodes: React.ReactNode[] = [];
    for (const group of groups) {
      const isOpen = expanded.has(group.key);
      nodes.push(
        <TableRow
          key={`g-${group.key}`}
          className="cursor-pointer bg-muted/40 font-medium hover:bg-muted/60"
          onClick={() => toggleExpand(group.key)}
        >
          <TableCell colSpan={4} className="py-2.5">
            <div className="flex items-center gap-2">
              {isOpen ? (
                <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
              ) : (
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              )}
              <span>{group.label}</span>
              <Badge variant="secondary" className="ml-1 text-xs font-normal">
                {group.rows.length} {group.rows.length === 1 ? "registro" : "registros"}
              </Badge>
            </div>
          </TableCell>
          <TableCell className="text-right">
            <Num n={group.sumRegistrados} />
          </TableCell>
          <TableCell className="text-right">
            <Num n={group.sumAsignados} />
          </TableCell>
          <TableCell className="text-right">
            <Num
              n={group.sumDisponibles}
              ok={group.sumDisponibles > 0}
              warn={group.sumDisponibles === 0}
            />
          </TableCell>
          <TableCell>
            <VigenteBadge vigente={group.anyVigente} />
          </TableCell>
          {canWrite ? <TableCell /> : null}
        </TableRow>,
      );
      if (isOpen) {
        for (const row of group.rows) {
          nodes.push(
            <DataRow
              key={`r-${row.id}`}
              row={row}
              canWrite={canWrite}
              indent
              onEdit={() => {
                setEditing(row);
                setDialogOpen(true);
              }}
              onDelete={() => setDeleting(row)}
            />,
          );
        }
      }
    }
    return nodes;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groups, expanded, canWrite]);

  return (
    <div>
      <PageHeader
        title="Determinación de campos de formación"
        description="Campos de formación determinados por sede docente y carrera profesional (CONAPRES)."
        actions={
          canWrite ? (
            <Button
              onClick={() => {
                setEditing(null);
                setDialogOpen(true);
              }}
            >
              Nuevo
            </Button>
          ) : undefined
        }
      />

      {/* ── Filters ── */}
      <div className="mb-4 grid gap-3">
        <Input
          placeholder="Buscar por ámbito, red, sede, carrera…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:max-w-sm"
        />

        <div className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1.5">
            <Label className="text-xs text-muted-foreground">Ámbito geográfico</Label>
            <div className="w-56">
              <EntityCombobox
                endpoint="health-geographic-scopes"
                value={filterAmbitoId}
                onChange={setFilterAmbitoId}
                placeholder="Todos"
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label className="text-xs text-muted-foreground">Sede docente</Label>
            <div className="w-64">
              <EntityCombobox
                endpoint="ipress"
                params={{ es_sede_docente: "true" }}
                toLabel={ipressLabel}
                value={filterIpress}
                onChange={setFilterIpress}
                placeholder="Todas"
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label className="text-xs text-muted-foreground">Carrera profesional</Label>
            <div className="w-52">
              <EntityCombobox
                endpoint="professional-careers"
                value={filterCarrera}
                onChange={setFilterCarrera}
                placeholder="Todas"
              />
            </div>
          </div>
          {hasFilters ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-8"
              onClick={() => {
                setFilterAmbitoId(null);
                setFilterIpress(null);
                setFilterCarrera(null);
                setSearch("");
              }}
            >
              Limpiar filtros
            </Button>
          ) : null}
        </div>

        {/* ── Grouping control ── */}
        <div className="flex items-center gap-2">
          <Label className="whitespace-nowrap text-xs text-muted-foreground">Agrupar por:</Label>
          <Select
            value={groupMode}
            onValueChange={(v) => {
              if (v) {
                setGroupMode(v as GroupMode);
                setExpanded(new Set());
              }
            }}
          >
            <SelectTrigger className="h-8 w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Sin agrupar</SelectItem>
              <SelectItem value="ambito">Ámbito geográfico</SelectItem>
              <SelectItem value="red">Red</SelectItem>
              <SelectItem value="sede">Sede docente</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground">
            {allRows.length} {allRows.length === 1 ? "registro" : "registros"}
            {list.isFetching ? " · actualizando…" : ""}
          </span>
        </div>
      </div>

      {/* ── Table ── */}
      {list.isError ? (
        <div className="rounded-md border border-destructive/30 p-4">
          <p className="text-sm text-destructive">No se pudo cargar el listado.</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => list.refetch()}
            disabled={list.isFetching}
          >
            {list.isFetching ? "Reintentando…" : "Reintentar"}
          </Button>
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ámbito geográfico</TableHead>
                <TableHead>Red</TableHead>
                <TableHead>Sede docente</TableHead>
                <TableHead>Carrera profesional</TableHead>
                <TableHead className="text-right">Determinados</TableHead>
                <TableHead className="text-right">Asignados</TableHead>
                <TableHead className="text-right">Disponibles</TableHead>
                <TableHead>Conv. específico</TableHead>
                {canWrite ? <TableHead className="w-24" /> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.isLoading ? (
                <TableRow>
                  <TableCell
                    colSpan={colCount}
                    className="py-8 text-center text-sm text-muted-foreground"
                  >
                    Cargando…
                  </TableCell>
                </TableRow>
              ) : allRows.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={colCount}
                    className="py-8 text-center text-sm text-muted-foreground"
                  >
                    Sin resultados.
                  </TableCell>
                </TableRow>
              ) : groupMode !== "none" ? (
                groupedTableRows
              ) : (
                allRows.map((row) => (
                  <DataRow
                    key={row.id}
                    row={row}
                    canWrite={canWrite}
                    onEdit={() => {
                      setEditing(row);
                      setDialogOpen(true);
                    }}
                    onDelete={() => setDeleting(row)}
                  />
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* ── CRUD Dialog ── */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editing
                ? "Editar determinación de campos de formación"
                : "Nueva determinación de campos de formación"}
            </DialogTitle>
          </DialogHeader>
          <ResourceForm
            fields={
              editing
                ? (clinicalFieldRegistrationsConfig.editFields ?? clinicalFieldRegistrationsConfig.fields)
                : (clinicalFieldRegistrationsConfig.createFields ?? clinicalFieldRegistrationsConfig.fields)
            }
            initial={editing as Record<string, unknown> | null}
            submitting={createM.isPending || updateM.isPending}
            onSubmit={onSubmit}
            onCancel={() => setDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* ── Delete Confirm ── */}
      <Dialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar determinación</DialogTitle>
            <DialogDescription>
              Esta acción no se puede deshacer. ¿Deseas continuar?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleting(null)}
              disabled={removeM.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={removeM.isPending}
            >
              {removeM.isPending ? "Procesando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
