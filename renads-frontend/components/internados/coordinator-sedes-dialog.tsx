"use client";

import React, { useMemo, useState } from "react";
import { toast } from "sonner";

import {
  useCoordinatorSedes,
  useAddCoordinatorSede,
  useDeleteCoordinatorSede,
  useCoordinatorTutors,
  useAddCoordinatorTutor,
  useDeleteCoordinatorTutor,
  useSedesDisponibles,
} from "@/lib/internados/coordinator";
import { extractApiError } from "@/lib/api/errors";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import type { WithId } from "@/lib/api/query";

export interface CoordinatorSedesDialogProps {
  coordinatorId: number;
  /** Nombre completo del coordinador (se muestra en el título del dialog). */
  coordinatorNombre: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Id de la universidad del alcance actual (puede ser null si no hay universidad resuelta). */
  universidad: number | null;
  /** Gating: solo `Universidad` / `Administrador RENADS` pueden escribir. */
  canWrite: boolean;
}

/** Helper para mostrar apellidos y nombres de un objeto genérico. */
function apellidosNombresInline(row: WithId): string {
  return [row.apellido_paterno, row.apellido_materno, row.nombres]
    .map((x) => String(x ?? "").trim())
    .filter(Boolean)
    .join(" ");
}

/**
 * Dialog de gestión de sedes y tutores de un coordinador.
 *
 * - Sección 1 — Lista de sedes actuales con botón expandir para ver/gestionar tutores.
 * - Sección 2 — Formulario para agregar nueva sede (solo `canWrite`).
 *
 * Contrato: docs/api-internados.md §Coordinadores
 */
export function CoordinatorSedesDialog({
  coordinatorId,
  coordinatorNombre,
  open,
  onOpenChange,
  universidad,
  canWrite,
}: CoordinatorSedesDialogProps) {
  const [sedeExpandida, setSedeExpandida] = useState<number | null>(null);
  const [tutorSeleccionado, setTutorSeleccionado] = useState<number | null>(null);
  const [ipressSeleccionada, setIpressSeleccionada] = useState<string | null>(null);

  // Sedes del coordinador
  const { data: sedes, isLoading: loadingSedes } = useCoordinatorSedes(coordinatorId);

  // Sedes disponibles para agregar (endpoint sedes-disponibles)
  const { data: sedesDisponibles, isLoading: loadingDisponibles } =
    useSedesDisponibles(coordinatorId);

  // Tutores de la sede expandida
  const { data: tutoresSede, isLoading: loadingTutores } = useCoordinatorTutors(
    coordinatorId,
    sedeExpandida,
  );

  // Mutaciones de sedes
  const addSedeMutation = useAddCoordinatorSede(coordinatorId);
  const deleteSedeMutation = useDeleteCoordinatorSede(coordinatorId);

  // Mutaciones de tutores (sedePk con fallback 0; los botones se deshabilitan si sedeExpandida == null)
  const addTutorMutation = useAddCoordinatorTutor(coordinatorId, sedeExpandida ?? 0);
  const deleteTutorMutation = useDeleteCoordinatorTutor(coordinatorId, sedeExpandida ?? 0);

  // Params para el selector de tutores al asignar (filtrar por universidad del alcance)
  const tutorParams = useMemo<Record<string, string> | undefined>(() => {
    if (universidad == null) return undefined;
    return { universidades: String(universidad) };
  }, [universidad]);

  function handleAgregarSede() {
    if (ipressSeleccionada == null) return;
    addSedeMutation.mutate(
      { ipress: ipressSeleccionada },
      {
        onSuccess: () => {
          toast.success("Sede agregada correctamente.");
          setIpressSeleccionada(null);
        },
        onError: (e) => toast.error(extractApiError(e)),
      },
    );
  }

  function handleEliminarSede(sedePk: number) {
    deleteSedeMutation.mutate(sedePk, {
      onSuccess: () => {
        toast.success("Sede eliminada.");
        // Si la sede eliminada estaba expandida, colapsar
        if (sedeExpandida === sedePk) {
          setSedeExpandida(null);
          setTutorSeleccionado(null);
        }
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  function handleAsignarTutor() {
    if (tutorSeleccionado == null || sedeExpandida == null) return;
    addTutorMutation.mutate(
      { tutor: tutorSeleccionado },
      {
        onSuccess: () => {
          toast.success("Tutor asignado correctamente.");
          setTutorSeleccionado(null);
        },
        onError: (e) => toast.error(extractApiError(e)),
      },
    );
  }

  function handleDesasignarTutor(tutorAsignadoId: number) {
    if (sedeExpandida == null) return;
    deleteTutorMutation.mutate(tutorAsignadoId, {
      onSuccess: () => toast.success("Tutor desasignado."),
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Sedes del coordinador — {coordinatorNombre}</DialogTitle>
        </DialogHeader>

        {/* Sección 1 — Lista de sedes actuales */}
        <div className="flex flex-col gap-2">
          {loadingSedes ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Cargando sedes asignadas…
            </div>
          ) : !sedes || sedes.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              Este coordinador no tiene sedes asignadas.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                      Universidad
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                      IPRESS (sede docente)
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                      Tutores
                    </th>
                    {canWrite && (
                      <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                        Acciones
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {sedes.map((sede) => (
                    <React.Fragment key={sede.id}>
                      <tr className="border-b last:border-0">
                        <td className="px-3 py-2">
                          {sede.universidad_detalle.nombre}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground">
                          {sede.ipress_detalle.nombre}
                        </td>
                        <td className="px-3 py-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setSedeExpandida(
                                sedeExpandida === sede.id ? null : sede.id,
                              )
                            }
                          >
                            {sedeExpandida === sede.id
                              ? "Ocultar tutores"
                              : "Ver tutores"}
                          </Button>
                        </td>
                        {canWrite && (
                          <td className="px-3 py-2 text-right">
                            <Button
                              variant="destructive"
                              size="sm"
                              disabled={deleteSedeMutation.isPending}
                              onClick={() => handleEliminarSede(sede.id)}
                            >
                              Eliminar sede
                            </Button>
                          </td>
                        )}
                      </tr>

                      {/* Sub-sección de tutores por sede */}
                      {sedeExpandida === sede.id && (
                        <tr key={`tutores-${sede.id}`} className="bg-muted/20">
                          <td colSpan={canWrite ? 4 : 3} className="px-4 py-3">
                            <div className="flex flex-col gap-3">
                              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                                Tutores — {sede.ipress_detalle.nombre}
                              </p>

                              {loadingTutores ? (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                                  Cargando tutores…
                                </div>
                              ) : !tutoresSede || tutoresSede.length === 0 ? (
                                <p className="text-sm text-muted-foreground">
                                  No hay tutores asignados a esta sede.
                                </p>
                              ) : (
                                <div className="overflow-x-auto rounded border">
                                  <table className="w-full text-sm">
                                    <thead>
                                      <tr className="border-b bg-background">
                                        <th className="px-3 py-1.5 text-left font-medium text-muted-foreground">
                                          Apellidos y nombres
                                        </th>
                                        <th className="px-3 py-1.5 text-left font-medium text-muted-foreground">
                                          N° documento
                                        </th>
                                        {canWrite && (
                                          <th className="px-3 py-1.5 text-right font-medium text-muted-foreground">
                                            Acción
                                          </th>
                                        )}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {tutoresSede.map((ct) => (
                                        <tr key={ct.id} className="border-b last:border-0">
                                          <td className="px-3 py-1.5">
                                            {apellidosNombresInline(ct.tutor_detalle as WithId)}
                                          </td>
                                          <td className="px-3 py-1.5 text-muted-foreground">
                                            {ct.tutor_detalle.numero_documento}
                                          </td>
                                          {canWrite && (
                                            <td className="px-3 py-1.5 text-right">
                                              <Button
                                                variant="destructive"
                                                size="sm"
                                                disabled={
                                                  deleteTutorMutation.isPending ||
                                                  sedeExpandida == null
                                                }
                                                onClick={() =>
                                                  handleDesasignarTutor(ct.id)
                                                }
                                              >
                                                Desasignar
                                              </Button>
                                            </td>
                                          )}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}

                              {/* Formulario de asignación de tutor (solo canWrite) */}
                              {canWrite && (
                                <div className="flex flex-col gap-2 pt-1">
                                  <div className="grid gap-1.5">
                                    <Label className="text-sm font-medium">
                                      Asignar tutor
                                    </Label>
                                    <div className="flex items-center gap-2">
                                      <div className="flex-1">
                                        <EntityCombobox<number>
                                          key={`tutor-${universidad ?? 0}`}
                                          endpoint="tutors"
                                          params={tutorParams}
                                          toLabel={(r) => apellidosNombresInline(r)}
                                          value={tutorSeleccionado}
                                          onChange={setTutorSeleccionado}
                                          placeholder="Buscar tutor…"
                                          disabled={sedeExpandida == null}
                                        />
                                      </div>
                                      <Button
                                        size="sm"
                                        onClick={handleAsignarTutor}
                                        disabled={
                                          tutorSeleccionado == null ||
                                          addTutorMutation.isPending ||
                                          sedeExpandida == null
                                        }
                                      >
                                        {addTutorMutation.isPending
                                          ? "Asignando…"
                                          : "Asignar"}
                                      </Button>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Sección 2 — Formulario para agregar sede (solo canWrite) */}
        {canWrite && (
          <>
            {/* Separador visual con etiqueta */}
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Agregar sede
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <div className="flex flex-col gap-3">
              {/* Selector de IPRESS (sedes disponibles para este coordinador) */}
              <div className="grid gap-1.5">
                <Label className="text-sm font-medium">IPRESS (sede docente)</Label>
                {loadingDisponibles ? (
                  <div className="flex items-center gap-2 py-1 text-sm text-muted-foreground">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Cargando sedes disponibles…
                  </div>
                ) : sedesDisponibles && sedesDisponibles.length > 0 ? (
                  <Select
                    value={ipressSeleccionada ?? ""}
                    onValueChange={setIpressSeleccionada}
                  >
                    <SelectTrigger className="w-full">
                      <span className={ipressSeleccionada == null ? "text-muted-foreground text-sm" : "text-sm"}>
                        {ipressSeleccionada != null
                          ? (sedesDisponibles.find((s) => s.id === ipressSeleccionada)?.nombre ?? ipressSeleccionada)
                          : "Selecciona una IPRESS…"}
                      </span>
                    </SelectTrigger>
                    <SelectContent>
                      {sedesDisponibles.map((sede) => (
                        <SelectItem key={sede.id} value={sede.id}>
                          {sede.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No hay sedes disponibles para este coordinador.
                  </p>
                )}
              </div>

              {/* Botón Agregar */}
              <div className="flex justify-end">
                <Button
                  onClick={handleAgregarSede}
                  disabled={
                    ipressSeleccionada == null ||
                    addSedeMutation.isPending ||
                    loadingDisponibles
                  }
                >
                  {addSedeMutation.isPending ? "Agregando…" : "Agregar sede"}
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
