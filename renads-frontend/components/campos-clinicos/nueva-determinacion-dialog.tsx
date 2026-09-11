"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Search } from "lucide-react";

import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { resourceKeys } from "@/lib/api/query";
import { extractApiError } from "@/lib/api/errors";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const ENDPOINT = "clinical-field-registrations";

const ipressLabel = (r: WithId) =>
  [r.codigo_renipress, r.nombre].filter(Boolean).join(" — ") || String(r.id);

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  pregradoId: number | null;
}

export function NuevaDeterminacionDialog({
  open,
  onOpenChange,
  onSuccess,
  pregradoId,
}: Props) {
  const qc = useQueryClient();

  const [nivel, setNivel] = useState<number | null>(null);
  const [sede, setSede] = useState<string | null>(null);
  const [carreraGlobal, setCarreraGlobal] = useState<number | null>(null);
  const [nroResolucion, setNroResolucion] = useState("");
  const [fechaResolucion, setFechaResolucion] = useState("");
  const [cantidades, setCantidades] = useState<Map<number, string>>(new Map());
  const [listSearch, setListSearch] = useState("");

  const efectivoNivel = nivel ?? pregradoId;
  const esPregrado = efectivoNivel === pregradoId && pregradoId !== null;

  const carrerasQuery = useQuery({
    queryKey: ["professional-careers", "det-dialog", efectivoNivel],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/professional-careers/", {
          params: { nivel_academico: efectivoNivel, page_size: 200, ordering: "nombre" },
        })
        .then((r) => r.data.results),
    enabled: esPregrado && efectivoNivel !== null,
    staleTime: 5 * 60_000,
  });

  const especialidadesQuery = useQuery({
    queryKey: ["specialties", "det-dialog"],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/specialties/", {
          params: { page_size: 500, ordering: "nombre" },
        })
        .then((r) => r.data.results),
    enabled: !esPregrado && efectivoNivel !== null,
    staleTime: 5 * 60_000,
  });

  const allRows = esPregrado ? (carrerasQuery.data ?? []) : (especialidadesQuery.data ?? []);
  const isLoadingRows = esPregrado ? carrerasQuery.isLoading : especialidadesQuery.isLoading;

  const rows = useMemo(() => {
    if (!listSearch.trim()) return allRows;
    const q = listSearch.toLowerCase();
    return allRows.filter((r) => String(r.nombre ?? "").toLowerCase().includes(q));
  }, [allRows, listSearch]);

  const cantConValor = useMemo(
    () => allRows.filter((r) => Number(cantidades.get(r.id) ?? 0) > 0),
    [allRows, cantidades],
  );

  const batchM = useMutation({
    mutationFn: async () => {
      if (!sede) throw new Error("Selecciona una sede docente.");
      if (cantConValor.length === 0)
        throw new Error("Ingresa al menos una cantidad mayor a 0.");
      if (!esPregrado && !carreraGlobal)
        throw new Error("Selecciona la carrera profesional.");

      const results = await Promise.allSettled(
        cantConValor.map((row) => {
          const payload: Record<string, unknown> = {
            ipress: sede,
            campos_clinicos_registrados: Number(cantidades.get(row.id)),
          };
          if (nroResolucion.trim())
            payload.numero_resolucion_conapres = nroResolucion.trim();
          if (fechaResolucion) payload.fecha_resolucion_conapres = fechaResolucion;
          if (esPregrado) {
            payload.carrera_profesional = row.id;
          } else {
            payload.especialidad = row.id;
            payload.carrera_profesional = carreraGlobal;
          }
          return api.post(`/${ENDPOINT}/`, payload);
        }),
      );

      const errors = results.filter(
        (r): r is PromiseRejectedResult => r.status === "rejected",
      );
      const creados = results.length - errors.length;
      return { creados, errors };
    },
    onSuccess: ({ creados, errors }) => {
      qc.invalidateQueries({ queryKey: resourceKeys.all(ENDPOINT) });
      if (creados > 0) {
        toast.success(
          `${creados} registro${creados === 1 ? "" : "s"} creado${creados === 1 ? "" : "s"}.`,
        );
        onSuccess();
      }
      if (errors.length > 0) {
        toast.error(
          `${errors.length} no se pudo${errors.length === 1 ? "" : "n"} guardar. ` +
            extractApiError(errors[0].reason),
        );
      }
      if (creados > 0) handleClose();
    },
    onError: (e) => toast.error(extractApiError(e)),
  });

  function reset() {
    setNivel(null);
    setSede(null);
    setCarreraGlobal(null);
    setNroResolucion("");
    setFechaResolucion("");
    setCantidades(new Map());
    setListSearch("");
  }

  function handleClose() {
    onOpenChange(false);
    reset();
  }

  function setCantidad(id: number, val: string) {
    setCantidades((prev) => {
      const next = new Map(prev);
      if (val === "" || val === "0") next.delete(id);
      else next.set(id, val);
      return next;
    });
  }

  const canSubmit = !!sede && cantConValor.length > 0 && !batchM.isPending;

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) handleClose();
        else onOpenChange(true);
      }}
    >
      <DialogContent
        className="p-0 gap-0 overflow-hidden"
        style={{ maxWidth: "min(90vw, 1100px)", width: "1100px", height: "min(88dvh, 680px)" }}
      >
        <DialogTitle className="sr-only">
          Nueva determinación de campos de formación
        </DialogTitle>

        <div className="flex h-full">
          {/* ── Panel izquierdo: configuración + acciones ── */}
          <div className="w-60 shrink-0 border-r flex flex-col">
            {/* Cabecera */}
            <div className="px-4 py-4 border-b pr-10">
              <p className="text-sm font-semibold leading-snug">
                Nueva determinación
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Campos de formación
              </p>
            </div>

            {/* Campos del formulario */}
            <div className="flex-1 flex flex-col gap-3 p-4 overflow-y-auto min-h-0">
              <div className="grid gap-1.5">
                <Label className="text-xs">
                  Nivel académico <span className="text-destructive">*</span>
                </Label>
                <EntityCombobox
                  endpoint="academic-levels"
                  value={efectivoNivel}
                  onChange={(id) => {
                    setNivel(id as number | null);
                    setCantidades(new Map());
                    setCarreraGlobal(null);
                    setListSearch("");
                  }}
                  placeholder="Seleccionar…"
                />
              </div>

              <div className="grid gap-1.5">
                <Label className="text-xs">
                  Sede docente <span className="text-destructive">*</span>
                </Label>
                <EntityCombobox
                  endpoint="ipress"
                  valueKey="codigo_renipress"
                  params={{ es_sede_docente: "true" }}
                  toLabel={ipressLabel}
                  value={sede}
                  onChange={setSede}
                  placeholder="Seleccionar…"
                />
              </div>

              {!esPregrado && efectivoNivel !== null ? (
                <div className="grid gap-1.5">
                  <Label className="text-xs">
                    Carrera profesional <span className="text-destructive">*</span>
                  </Label>
                  <EntityCombobox
                    endpoint="professional-careers"
                    value={carreraGlobal}
                    onChange={(id) => setCarreraGlobal(id as number | null)}
                    placeholder="Seleccionar…"
                  />
                </div>
              ) : null}

              <div className="border-t pt-3 grid gap-3">
                <div className="grid gap-1.5">
                  <Label htmlFor="nro-res-new" className="text-xs">
                    N° Resolución CONAPRES
                  </Label>
                  <Input
                    id="nro-res-new"
                    value={nroResolucion}
                    onChange={(e) => setNroResolucion(e.target.value)}
                    placeholder="001-2025-CONAPRES"
                    className="h-8 text-sm"
                  />
                </div>

                <div className="grid gap-1.5">
                  <Label htmlFor="fecha-res-new" className="text-xs">
                    Fecha resolución CONAPRES
                  </Label>
                  <Input
                    id="fecha-res-new"
                    type="date"
                    value={fechaResolucion}
                    onChange={(e) => setFechaResolucion(e.target.value)}
                    className="h-8 text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Footer: resumen + acciones */}
            <div className="p-4 border-t flex flex-col gap-2.5">
              {cantConValor.length > 0 ? (
                <Badge variant="secondary" className="self-start text-xs py-0.5">
                  {cantConValor.length}{" "}
                  {cantConValor.length === 1 ? "registro" : "registros"} a guardar
                </Badge>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Ingresa cantidades en la tabla →
                </p>
              )}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={handleClose}
                  disabled={batchM.isPending}
                >
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  className="flex-1"
                  onClick={() => batchM.mutate()}
                  disabled={!canSubmit}
                >
                  {batchM.isPending ? "Guardando…" : "Guardar"}
                </Button>
              </div>
            </div>
          </div>

          {/* ── Panel derecho: lista de cantidades ── */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Cabecera del panel derecho */}
            <div className="px-4 py-3 border-b flex items-center gap-2 shrink-0 pr-12">
              <span className="text-sm text-muted-foreground flex-1">
                {esPregrado ? "Carreras profesionales" : "Especialidades"}
                {allRows.length > 0 ? (
                  <span className="ml-1 text-xs">({allRows.length})</span>
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

            {/* Lista scrollable */}
            <div className="flex-1 overflow-y-auto">
              {efectivoNivel === null ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">
                    Selecciona nivel académico para ver las opciones.
                  </p>
                </div>
              ) : isLoadingRows ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">Cargando…</p>
                </div>
              ) : rows.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">Sin resultados.</p>
                </div>
              ) : (
                <Table className="table-fixed w-full">
                  <colgroup>
                    <col />
                    <col style={{ width: "160px" }} />
                  </colgroup>
                  <TableHeader className="sticky top-0 bg-background z-10 border-b">
                    <TableRow>
                      <TableHead className="text-xs h-9">
                        {esPregrado ? "Carrera profesional" : "Especialidad"}
                      </TableHead>
                      <TableHead className="text-xs h-9 text-right pr-4">
                        Campos det.
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row) => (
                      <TableRow
                        key={row.id}
                        className={
                          cantidades.has(row.id)
                            ? "bg-primary/5"
                            : "hover:bg-muted/40"
                        }
                      >
                        <TableCell className="py-1.5 text-sm overflow-hidden">
                          <span
                            className="block truncate"
                            title={String(row.nombre ?? row.id)}
                          >
                            {String(row.nombre ?? row.id)}
                          </span>
                        </TableCell>
                        <TableCell className="py-1 pr-4">
                          <Input
                            type="number"
                            min={1}
                            value={cantidades.get(row.id) ?? ""}
                            onChange={(e) => setCantidad(row.id, e.target.value)}
                            placeholder="—"
                            className="h-7 w-28 ml-auto text-right tabular-nums"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
