"use client";

import { useState, useEffect, useMemo } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, Search } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { resourceKeys } from "@/lib/api/query";
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
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const ENDPOINT = "clinical-field-allocations";

function rowLabel(row: WithId, esPregrado: boolean): string {
  if (esPregrado) {
    const cp = row.carrera_profesional_detalle as WithId | null;
    return String(cp?.nombre ?? row.carrera_profesional ?? "—");
  }
  const esp = row.especialidad_detalle as WithId | null;
  return String(esp?.nombre ?? row.especialidad ?? "—");
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ipressNombre: string;
  univNombre: string;
  convenioLabel: string;
  rows: WithId[];
  esPregrado: boolean;
  onSuccess: () => void;
}

export function EditarAsignacionDialog({
  open,
  onOpenChange,
  ipressNombre,
  univNombre,
  convenioLabel,
  rows,
  esPregrado,
  onSuccess,
}: Props) {
  const qc = useQueryClient();

  const [quantities, setQuantities] = useState<Map<number, string>>(new Map());
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [listSearch, setListSearch] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deletedIds, setDeletedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (open && rows.length > 0) {
      const map = new Map<number, string>();
      rows.forEach((r) =>
        map.set(r.id, String(r.campos_clinicos_autorizados ?? "")),
      );
      setQuantities(map);
      const first = rows[0];
      setFechaInicio(String(first.fecha_inicio ?? ""));
      setFechaFin(String(first.fecha_fin ?? ""));
      setListSearch("");
      setDeletingId(null);
      setDeletedIds(new Set());
    }
  }, [open, rows]);

  const activeRows = useMemo(
    () => rows.filter((r) => !deletedIds.has(r.id)),
    [rows, deletedIds],
  );

  const filteredRows = useMemo(() => {
    if (!listSearch.trim()) return activeRows;
    const q = listSearch.toLowerCase();
    return activeRows.filter((r) =>
      rowLabel(r, esPregrado).toLowerCase().includes(q),
    );
  }, [activeRows, listSearch, esPregrado]);

  const totals = useMemo(
    () => ({
      actual: activeRows.reduce(
        (s, r) => s + Number(r.campos_clinicos_autorizados ?? 0),
        0,
      ),
      nuevo: activeRows.reduce(
        (s, r) =>
          s +
          Number(quantities.get(r.id) ?? r.campos_clinicos_autorizados ?? 0),
        0,
      ),
    }),
    [activeRows, quantities],
  );

  const saveM = useMutation({
    mutationFn: async () => {
      if (activeRows.length === 0) throw new Error("No hay registros activos.");
      const results = await Promise.allSettled(
        activeRows.map((r) => {
          const qty = Number(
            quantities.get(r.id) ?? r.campos_clinicos_autorizados ?? 0,
          );
          return api.patch(`/${ENDPOINT}/${r.id}/`, {
            campos_clinicos_autorizados: qty,
            fecha_inicio: fechaInicio || null,
            fecha_fin: fechaFin || null,
          });
        }),
      );
      const errors = results.filter(
        (r): r is PromiseRejectedResult => r.status === "rejected",
      );
      return { saved: results.length - errors.length, errors };
    },
    onSuccess: ({ saved, errors }) => {
      qc.invalidateQueries({ queryKey: resourceKeys.all(ENDPOINT) });
      if (saved > 0) {
        toast.success(
          `${saved} registro${saved !== 1 ? "s" : ""} actualizado${saved !== 1 ? "s" : ""}.`,
        );
        onSuccess();
        onOpenChange(false);
      }
      if (errors.length > 0) {
        toast.error(
          `${errors.length} no se pudo${errors.length !== 1 ? "n" : ""} actualizar. ` +
            extractApiError(errors[0].reason),
        );
      }
    },
    onError: (e) => toast.error(extractApiError(e)),
  });

  const deleteM = useMutation({
    mutationFn: (id: number) => api.delete(`/${ENDPOINT}/${id}/`),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: resourceKeys.all(ENDPOINT) });
      toast.success("Registro eliminado.");
      setDeletingId(null);
      setDeletedIds((prev) => new Set([...prev, id]));
      onSuccess();
      if (activeRows.length <= 1) onOpenChange(false);
    },
    onError: (e) => toast.error(extractApiError(e)),
  });

  function setQty(id: number, val: string) {
    setQuantities((prev) => {
      const next = new Map(prev);
      next.set(id, val);
      return next;
    });
  }

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(v) => {
          if (!v) onOpenChange(false);
        }}
      >
        <DialogContent
          className="p-0 gap-0 overflow-hidden flex flex-col"
          style={{
            maxWidth: "min(90vw, 1050px)",
            width: "1050px",
            maxHeight: "min(88dvh, 660px)",
          }}
        >
          <DialogTitle className="sr-only">
            Editar asignación — {ipressNombre} / {univNombre}
          </DialogTitle>

          <div className="flex flex-1 min-h-0">
            {/* ── Panel izquierdo ── */}
            <div className="w-64 shrink-0 border-r flex flex-col">
              <div className="px-4 py-4 border-b pr-10">
                <p className="text-sm font-semibold leading-snug">
                  Editar asignación
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Campos de formación
                </p>
              </div>

              <div className="flex-1 flex flex-col gap-3 p-4 overflow-y-auto min-h-0">
                <div className="grid gap-1">
                  <span className="text-xs text-muted-foreground">
                    Sede docente
                  </span>
                  <span className="text-sm font-medium leading-snug">
                    {ipressNombre}
                  </span>
                </div>
                <div className="grid gap-1">
                  <span className="text-xs text-muted-foreground">
                    Universidad
                  </span>
                  <span className="text-sm font-medium leading-snug">
                    {univNombre}
                  </span>
                </div>
                <div className="grid gap-1">
                  <span className="text-xs text-muted-foreground">Convenio</span>
                  <span className="text-sm font-medium leading-snug break-words">
                    {convenioLabel}
                  </span>
                </div>

                <div className="border-t pt-3 grid gap-3">
                  <div className="grid gap-1.5">
                    <Label htmlFor="edit-asig-fi" className="text-xs">
                      Fecha inicio
                    </Label>
                    <Input
                      id="edit-asig-fi"
                      type="date"
                      value={fechaInicio}
                      onChange={(e) => setFechaInicio(e.target.value)}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div className="grid gap-1.5">
                    <Label htmlFor="edit-asig-ff" className="text-xs">
                      Fecha fin
                    </Label>
                    <Input
                      id="edit-asig-ff"
                      type="date"
                      value={fechaFin}
                      onChange={(e) => setFechaFin(e.target.value)}
                      className="h-8 text-sm"
                    />
                  </div>
                </div>
              </div>

              <div className="p-4 border-t flex flex-col gap-2.5">
                <p className="text-xs text-muted-foreground">
                  {activeRows.length} carrera
                  {activeRows.length !== 1 ? "s" : ""} asignada
                  {activeRows.length !== 1 ? "s" : ""}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => onOpenChange(false)}
                    disabled={saveM.isPending}
                  >
                    Cancelar
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => saveM.mutate()}
                    disabled={activeRows.length === 0 || saveM.isPending}
                  >
                    {saveM.isPending ? "Guardando…" : "Guardar"}
                  </Button>
                </div>
              </div>
            </div>

            {/* ── Panel derecho ── */}
            <div className="flex-1 flex flex-col min-w-0">
              <div className="px-4 py-3 border-b flex items-center gap-2 shrink-0 pr-12">
                <span className="text-sm text-muted-foreground flex-1">
                  {esPregrado ? "Carreras profesionales" : "Especialidades"}
                  {activeRows.length > 0 ? (
                    <span className="ml-1 text-xs">({activeRows.length})</span>
                  ) : null}
                </span>
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
                  <Input
                    value={listSearch}
                    onChange={(e) => setListSearch(e.target.value)}
                    placeholder="Filtrar…"
                    className="h-7 w-36 pl-7 text-xs"
                  />
                </div>
              </div>

              <div className="flex-1 overflow-y-auto">
                {activeRows.length === 0 ? (
                  <div className="flex h-full items-center justify-center">
                    <p className="text-sm text-muted-foreground">
                      Sin registros.
                    </p>
                  </div>
                ) : (
                  <Table className="table-fixed w-full">
                    <colgroup>
                      <col />
                      <col style={{ width: "80px" }} />
                      <col style={{ width: "150px" }} />
                      <col style={{ width: "44px" }} />
                    </colgroup>
                    <TableHeader className="sticky top-0 bg-background z-10 border-b">
                      <TableRow>
                        <TableHead className="text-xs h-9">
                          {esPregrado ? "Carrera profesional" : "Especialidad"}
                        </TableHead>
                        <TableHead className="text-xs h-9 text-center px-2">
                          Actual
                        </TableHead>
                        <TableHead className="text-xs h-9 text-right pr-3">
                          Nuevo
                        </TableHead>
                        <TableHead className="text-xs h-9" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredRows.map((row) => {
                        const actual = Number(
                          row.campos_clinicos_autorizados ?? 0,
                        );
                        const qty = quantities.get(row.id) ?? String(actual);
                        const changed = Number(qty) !== actual;
                        const label = rowLabel(row, esPregrado);
                        return (
                          <TableRow
                            key={row.id}
                            className={
                              changed ? "bg-primary/5" : "hover:bg-muted/40"
                            }
                          >
                            <TableCell className="py-1.5 text-sm overflow-hidden">
                              <span
                                className="block truncate"
                                title={label}
                              >
                                {label}
                              </span>
                            </TableCell>
                            <TableCell className="py-1 text-center px-2 text-xs tabular-nums text-muted-foreground">
                              {actual || "—"}
                            </TableCell>
                            <TableCell className="py-1 pr-3">
                              <Input
                                type="number"
                                min={1}
                                value={qty}
                                onChange={(e) => setQty(row.id, e.target.value)}
                                className="h-7 w-28 ml-auto text-right tabular-nums"
                              />
                            </TableCell>
                            <TableCell className="py-1 px-1">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                aria-label="Eliminar este registro"
                                onClick={() => setDeletingId(row.id)}
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                    <TableFooter>
                      <TableRow className="border-t-2 font-semibold">
                        <TableCell className="py-2 text-xs">
                          Total ({activeRows.length} carrera
                          {activeRows.length !== 1 ? "s" : ""})
                        </TableCell>
                        <TableCell className="py-2 text-center px-2 text-xs tabular-nums">
                          {totals.actual || "—"}
                        </TableCell>
                        <TableCell className="py-2 pr-3 text-right text-xs tabular-nums font-bold">
                          {totals.nuevo || "—"}
                        </TableCell>
                        <TableCell />
                      </TableRow>
                    </TableFooter>
                  </Table>
                )}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Confirmación de borrado individual */}
      <Dialog
        open={deletingId !== null}
        onOpenChange={(v) => {
          if (!v) setDeletingId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar asignación</DialogTitle>
            <DialogDescription>
              Esta acción no se puede deshacer. ¿Deseas continuar?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingId(null)}
              disabled={deleteM.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deletingId !== null) deleteM.mutate(deletingId);
              }}
              disabled={deleteM.isPending}
            >
              {deleteM.isPending ? "Procesando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
