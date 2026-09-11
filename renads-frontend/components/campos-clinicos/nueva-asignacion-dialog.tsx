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
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const ENDPOINT = "clinical-field-allocations";

const ipressLabel = (r: WithId) =>
  [r.codigo_renipress, r.nombre].filter(Boolean).join(" — ") || String(r.id);

const convenioLabel = (r: WithId) =>
  String(r.nomenclatura ?? r.titulo ?? r.id);

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  pregradoId: number | null;
}

export function NuevaAsignacionDialog({
  open,
  onOpenChange,
  onSuccess,
  pregradoId,
}: Props) {
  const qc = useQueryClient();

  const [nivel, setNivel] = useState<number | null>(null);
  const [sede, setSede] = useState<string | null>(null);
  const [convenio, setConvenio] = useState<number | null>(null);
  const [fechaInicio, setFechaInicio] = useState("");
  const [fechaFin, setFechaFin] = useState("");
  const [cantidades, setCantidades] = useState<Map<number, string>>(new Map());
  const [listSearch, setListSearch] = useState("");

  const efectivoNivel = nivel ?? pregradoId;
  const esPregrado = efectivoNivel === pregradoId && pregradoId !== null;

  const registrationsQuery = useQuery({
    queryKey: ["clinical-field-registrations", "asig-nueva", sede, efectivoNivel],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/clinical-field-registrations/", {
          params: {
            ipress: sede,
            ...(efectivoNivel
              ? { "carrera_profesional__nivel_academico": String(efectivoNivel) }
              : {}),
            page_size: 200,
            ordering: esPregrado
              ? "carrera_profesional__nombre"
              : "especialidad__nombre",
          },
        })
        .then((r) => r.data.results),
    enabled: !!sede && efectivoNivel !== null,
    staleTime: 2 * 60_000,
  });

  const allRows = registrationsQuery.data ?? [];

  const rows = useMemo(() => {
    if (!listSearch.trim()) return allRows;
    const q = listSearch.toLowerCase();
    return allRows.filter((r) => {
      const cp = r.carrera_profesional_detalle as WithId | null;
      const esp = r.especialidad_detalle as WithId | null;
      return String(esPregrado ? cp?.nombre : esp?.nombre ?? "")
        .toLowerCase()
        .includes(q);
    });
  }, [allRows, listSearch, esPregrado]);

  const cantConValor = useMemo(
    () => allRows.filter((r) => Number(cantidades.get(r.id) ?? 0) > 0),
    [allRows, cantidades],
  );

  const batchM = useMutation({
    mutationFn: async () => {
      if (!sede) throw new Error("Selecciona una sede docente.");
      if (!convenio) throw new Error("Selecciona un convenio específico.");
      if (!fechaInicio) throw new Error("Ingresa la fecha de inicio.");
      if (!fechaFin) throw new Error("Ingresa la fecha de fin.");
      if (cantConValor.length === 0)
        throw new Error("Ingresa al menos una cantidad mayor a 0.");

      const results = await Promise.allSettled(
        cantConValor.map((row) =>
          api.post(`/${ENDPOINT}/`, {
            campo_clinico_ipress: row.id,
            convenio,
            fecha_inicio: fechaInicio,
            fecha_fin: fechaFin,
            campos_clinicos_autorizados: Number(cantidades.get(row.id)),
          }),
        ),
      );
      const errors = results.filter(
        (r): r is PromiseRejectedResult => r.status === "rejected",
      );
      return { creados: results.length - errors.length, errors };
    },
    onSuccess: ({ creados, errors }) => {
      qc.invalidateQueries({ queryKey: resourceKeys.all(ENDPOINT) });
      if (creados > 0) {
        toast.success(
          `${creados} asignación${creados !== 1 ? "es" : ""} creada${creados !== 1 ? "s" : ""}.`,
        );
        onSuccess();
        handleClose();
      }
      if (errors.length > 0) {
        toast.error(
          `${errors.length} no se pudo${errors.length !== 1 ? "n" : ""} guardar. ` +
            extractApiError(errors[0].reason),
        );
      }
    },
    onError: (e) => toast.error(extractApiError(e)),
  });

  function reset() {
    setNivel(null);
    setSede(null);
    setConvenio(null);
    setFechaInicio("");
    setFechaFin("");
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

  const canSubmit =
    !!sede &&
    !!convenio &&
    !!fechaInicio &&
    !!fechaFin &&
    cantConValor.length > 0 &&
    !batchM.isPending;

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
        style={{
          maxWidth: "min(90vw, 1100px)",
          width: "1100px",
          height: "min(88dvh, 700px)",
        }}
      >
        <DialogTitle className="sr-only">
          Nueva asignación de campos de formación
        </DialogTitle>

        <div className="flex h-full">
          {/* ── Panel izquierdo ── */}
          <div className="w-72 shrink-0 border-r flex flex-col">
            <div className="px-4 py-4 border-b pr-10">
              <p className="text-sm font-semibold leading-snug">Nueva asignación</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Campos de formación
              </p>
            </div>

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
                  onChange={(v) => {
                    setSede(v as string | null);
                    setCantidades(new Map());
                  }}
                  placeholder="Seleccionar…"
                />
              </div>

              <div className="grid gap-1.5">
                <Label className="text-xs">
                  Convenio específico <span className="text-destructive">*</span>
                </Label>
                <EntityCombobox
                  endpoint="conventions"
                  params={{ tipo_convenio: "Específico", estado_actual: "Vigente" }}
                  toLabel={convenioLabel}
                  value={convenio}
                  onChange={(id) => setConvenio(id as number | null)}
                  placeholder="Seleccionar…"
                />
              </div>

              <div className="border-t pt-3 grid gap-3">
                <div className="grid gap-1.5">
                  <Label htmlFor="asig-nueva-fi" className="text-xs">
                    Fecha inicio <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="asig-nueva-fi"
                    type="date"
                    value={fechaInicio}
                    onChange={(e) => setFechaInicio(e.target.value)}
                    className="h-8 text-sm"
                  />
                </div>
                <div className="grid gap-1.5">
                  <Label htmlFor="asig-nueva-ff" className="text-xs">
                    Fecha fin <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="asig-nueva-ff"
                    type="date"
                    value={fechaFin}
                    onChange={(e) => setFechaFin(e.target.value)}
                    className="h-8 text-sm"
                  />
                </div>
              </div>
            </div>

            <div className="p-4 border-t flex flex-col gap-2.5">
              {cantConValor.length > 0 ? (
                <Badge variant="secondary" className="self-start text-xs py-0.5">
                  {cantConValor.length}{" "}
                  {cantConValor.length === 1 ? "asignación" : "asignaciones"} a guardar
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

          {/* ── Panel derecho ── */}
          <div className="flex-1 flex flex-col min-w-0">
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

            <div className="flex-1 overflow-y-auto">
              {!sede || efectivoNivel === null ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">
                    Selecciona nivel académico y sede docente.
                  </p>
                </div>
              ) : registrationsQuery.isLoading ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">Cargando…</p>
                </div>
              ) : rows.length === 0 ? (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-muted-foreground">
                    Sin determinaciones para esta sede y nivel.
                  </p>
                </div>
              ) : (
                <Table className="table-fixed w-full">
                  <colgroup>
                    <col />
                    <col style={{ width: "80px" }} />
                    <col style={{ width: "150px" }} />
                  </colgroup>
                  <TableHeader className="sticky top-0 bg-background z-10 border-b">
                    <TableRow>
                      <TableHead className="text-xs h-9">
                        {esPregrado ? "Carrera profesional" : "Especialidad"}
                      </TableHead>
                      <TableHead className="text-xs h-9 text-center px-2">
                        Disponible
                      </TableHead>
                      <TableHead className="text-xs h-9 text-right pr-4">
                        Autorizar
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row) => {
                      const cp = row.carrera_profesional_detalle as WithId | null;
                      const esp = row.especialidad_detalle as WithId | null;
                      const label = String(
                        esPregrado ? cp?.nombre : esp?.nombre ?? "—",
                      );
                      const disponible = Number(row.disponibilidad ?? 0);
                      const qty = cantidades.get(row.id) ?? "";
                      const isSet = cantidades.has(row.id);
                      return (
                        <TableRow
                          key={row.id}
                          className={isSet ? "bg-primary/5" : "hover:bg-muted/40"}
                        >
                          <TableCell className="py-1.5 text-sm overflow-hidden">
                            <span className="block truncate" title={label}>
                              {label}
                            </span>
                          </TableCell>
                          <TableCell className="py-1 text-center px-2 text-xs tabular-nums text-muted-foreground">
                            {disponible || "—"}
                          </TableCell>
                          <TableCell className="py-1 pr-4">
                            <Input
                              type="number"
                              min={1}
                              max={disponible || undefined}
                              value={qty}
                              onChange={(e) => setCantidad(row.id, e.target.value)}
                              placeholder="—"
                              className="h-7 w-28 ml-auto text-right tabular-nums"
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })}
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
