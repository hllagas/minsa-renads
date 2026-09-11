"use client";

import { useState, useEffect } from "react";

import type { WithId } from "@/lib/api/query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editing: WithId | null;
  onSubmit: (payload: Record<string, unknown>) => void;
  isPending: boolean;
}

function detalleNombre(v: unknown): string {
  if (v && typeof v === "object" && "nombre" in v)
    return String((v as Record<string, unknown>).nombre ?? "—");
  return "—";
}

export function EditarDeterminacionDialog({
  open,
  onOpenChange,
  editing,
  onSubmit,
  isPending,
}: Props) {
  const [cantidad, setCantidad] = useState("");
  const [nroResolucion, setNroResolucion] = useState("");
  const [fechaResolucion, setFechaResolucion] = useState("");

  useEffect(() => {
    if (editing) {
      setCantidad(String(editing.campos_clinicos_registrados ?? ""));
      setNroResolucion(String(editing.numero_resolucion_conapres ?? ""));
      setFechaResolucion(String(editing.fecha_resolucion_conapres ?? ""));
    }
  }, [editing]);

  function handleSubmit() {
    const payload: Record<string, unknown> = {
      campos_clinicos_registrados: Number(cantidad),
    };
    if (nroResolucion.trim()) payload.numero_resolucion_conapres = nroResolucion.trim();
    else payload.numero_resolucion_conapres = null;
    if (fechaResolucion) payload.fecha_resolucion_conapres = fechaResolucion;
    else payload.fecha_resolucion_conapres = null;
    onSubmit(payload);
  }

  function handleClose() {
    onOpenChange(false);
  }

  const sede = detalleNombre(editing?.ipress_detalle);
  const carrera = detalleNombre(editing?.carrera_profesional_detalle);
  const especialidad = editing?.especialidad_detalle
    ? detalleNombre(editing.especialidad_detalle)
    : null;

  const registrados = Number(editing?.campos_clinicos_registrados ?? 0);
  const asignados = Number(editing?.campos_clinicos_asignados ?? 0);
  const disponibles = Number(editing?.disponibilidad ?? 0);

  const canSubmit = cantidad.trim() !== "" && Number(cantidad) >= 0 && !isPending;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); }}>
      <DialogContent
        className="p-0 gap-0 overflow-hidden"
        style={{ maxWidth: "min(90vw, 860px)", width: "860px", height: "min(88dvh, 480px)" }}
      >
        <DialogTitle className="sr-only">Editar determinación</DialogTitle>

        <div className="flex h-full">
          {/* ── Panel izquierdo: contexto de la determinación ── */}
          <div className="w-56 shrink-0 border-r flex flex-col">
            <div className="px-4 py-4 border-b pr-10">
              <p className="text-sm font-semibold">Editar determinación</p>
              <p className="text-xs text-muted-foreground mt-0.5">Campos de formación</p>
            </div>

            <div className="flex-1 p-4 flex flex-col gap-4 overflow-y-auto min-h-0">
              {/* Sede */}
              <div className="grid gap-1">
                <span className="text-xs text-muted-foreground">Sede docente</span>
                <span className="text-sm font-medium leading-snug">{sede}</span>
              </div>

              {/* Carrera */}
              <div className="grid gap-1">
                <span className="text-xs text-muted-foreground">Carrera profesional</span>
                <span className="text-sm font-medium leading-snug">{carrera}</span>
              </div>

              {/* Especialidad (solo si existe) */}
              {especialidad ? (
                <div className="grid gap-1">
                  <span className="text-xs text-muted-foreground">Especialidad</span>
                  <span className="text-sm font-medium leading-snug">{especialidad}</span>
                </div>
              ) : null}

              {/* Métricas actuales */}
              <div className="border-t pt-3 grid gap-2">
                <span className="text-xs text-muted-foreground">Valores actuales</span>
                <div className="flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="text-xs font-normal">
                    Det.{" "}
                    <span className="ml-1 font-semibold tabular-nums">{registrados}</span>
                  </Badge>
                  <Badge variant="outline" className="text-xs font-normal">
                    Asig.{" "}
                    <span className="ml-1 font-semibold tabular-nums">{asignados}</span>
                  </Badge>
                  <Badge
                    variant={disponibles === 0 && registrados > 0 ? "destructive" : "outline"}
                    className="text-xs font-normal"
                  >
                    Disp.{" "}
                    <span className="ml-1 font-semibold tabular-nums">{disponibles}</span>
                  </Badge>
                </div>
              </div>
            </div>
          </div>

          {/* ── Panel derecho: campos editables ── */}
          <div className="flex-1 flex flex-col min-w-0">
            <div className="px-4 py-3 border-b pr-12 shrink-0">
              <span className="text-sm text-muted-foreground">Actualizar valores</span>
            </div>

            <div className="flex-1 p-5 flex flex-col gap-4 overflow-y-auto min-h-0">
              <div className="grid gap-1.5">
                <Label htmlFor="edit-cantidad" className="text-sm font-medium">
                  Campos de formación determinados{" "}
                  <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="edit-cantidad"
                  type="number"
                  min={0}
                  value={cantidad}
                  onChange={(e) => setCantidad(e.target.value)}
                  className="h-9 w-36 tabular-nums"
                  autoFocus
                />
              </div>

              <div className="border-t pt-4 grid gap-4">
                <div className="grid gap-1.5">
                  <Label htmlFor="edit-nro-res" className="text-sm">
                    N° Resolución CONAPRES
                  </Label>
                  <Input
                    id="edit-nro-res"
                    value={nroResolucion}
                    onChange={(e) => setNroResolucion(e.target.value)}
                    placeholder="001-2025-CONAPRES"
                    className="h-9"
                  />
                </div>

                <div className="grid gap-1.5">
                  <Label htmlFor="edit-fecha-res" className="text-sm">
                    Fecha resolución CONAPRES
                  </Label>
                  <Input
                    id="edit-fecha-res"
                    type="date"
                    value={fechaResolucion}
                    onChange={(e) => setFechaResolucion(e.target.value)}
                    className="h-9 w-44"
                  />
                </div>
              </div>
            </div>

            {/* Footer acciones */}
            <div className="border-t px-5 py-4 flex flex-wrap justify-end gap-2 shrink-0">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={isPending}
              >
                Cancelar
              </Button>
              <Button onClick={handleSubmit} disabled={!canSubmit}>
                {isPending ? "Guardando…" : "Guardar cambios"}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
