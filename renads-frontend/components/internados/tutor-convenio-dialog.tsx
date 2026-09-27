"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";

import {
  useTutorConvenios,
  useAddTutorConvenio,
  useDeleteTutorConvenio,
  useConvenioEspecificoIds,
} from "@/lib/internados/tutor-convenio";
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

export interface TutorConvenioDialogProps {
  tutorId: number;
  /** Nombre completo del tutor (se muestra en el título del dialog). */
  tutorNombre: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Id de la universidad del alcance actual (puede ser null si no hay universidad resuelta). */
  universidad: number | null;
  /** Gating: solo `Universidad` / `Administrador RENADS` pueden escribir. */
  canWrite: boolean;
}

/**
 * Dialog de gestión de vínculos tutor × convenio × IPRESS.
 *
 * - Sección 1 — Lista de vínculos actuales (con botón «Eliminar» si canWrite).
 * - Sección 2 — Formulario de alta (solo si canWrite): selector de Convenio + IPRESS.
 *
 * Contrato: docs/api-internados.md §TutorConvenio
 */
export function TutorConvenioDialog({
  tutorId,
  tutorNombre,
  open,
  onOpenChange,
  universidad,
  canWrite,
}: TutorConvenioDialogProps) {
  const [convenioSeleccionado, setConvenioSeleccionado] = useState<number | null>(null);
  const [ipressSeleccionada, setIpressSeleccionada] = useState<string | null>(null);

  // Datos de vínculos actuales
  const { data: vinculos, isLoading: loadingVinculos } = useTutorConvenios(tutorId);

  // Mutaciones
  const addMutation = useAddTutorConvenio(tutorId);
  const deleteMutation = useDeleteTutorConvenio(tutorId);

  // Ids de tipo «Específico» y estado «Vigente» (resueltos en runtime sin hardcodear ids)
  const { especificoId, vigenteId } = useConvenioEspecificoIds();

  // Params del combo de convenios: Específicos vigentes de la universidad elegida
  const convenioParams = useMemo<Record<string, string> | undefined>(() => {
    if (universidad == null) return undefined;
    const p: Record<string, string> = { universidad: String(universidad) };
    if (especificoId != null) p.tipo_convenio = String(especificoId);
    if (vigenteId != null) p.estado_actual = String(vigenteId);
    return p;
  }, [universidad, especificoId, vigenteId]);

  // Params del combo de IPRESS: sedes docentes (el backend valida el ámbito del convenio al POST)
  const ipressParams = useMemo<Record<string, string>>(() => {
    return { es_sede_docente: "true" };
  }, []);

  function handleAgregar() {
    if (convenioSeleccionado == null || ipressSeleccionada == null) return;
    addMutation.mutate(
      { convenio: convenioSeleccionado, ipress: ipressSeleccionada },
      {
        onSuccess: () => {
          toast.success("Vínculo agregado correctamente.");
          setConvenioSeleccionado(null);
          setIpressSeleccionada(null);
        },
        onError: (e) => toast.error(extractApiError(e)),
      },
    );
  }

  function handleEliminar(vinculoId: number) {
    deleteMutation.mutate(vinculoId, {
      onSuccess: () => toast.success("Vínculo eliminado."),
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Convenios asignados — {tutorNombre}</DialogTitle>
        </DialogHeader>

        {/* Sección 1 — Lista de vínculos actuales */}
        <div className="flex flex-col gap-2">
          {loadingVinculos ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Cargando convenios asignados…
            </div>
          ) : !vinculos || vinculos.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              Este tutor no tiene convenios asignados.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                      Convenio
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                      IPRESS
                    </th>
                    {canWrite && (
                      <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                        Acción
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {vinculos.map((v) => (
                    <tr key={v.id} className="border-b last:border-0">
                      <td className="max-w-[240px] px-3 py-2">
                        <span className="line-clamp-2 leading-snug">
                          {v.convenio_detalle.nomenclatura
                            ? `${v.convenio_detalle.nomenclatura} — ${v.convenio_detalle.titulo}`
                            : v.convenio_detalle.titulo}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-muted-foreground">
                        {v.ipress_detalle.nombre}
                      </td>
                      {canWrite && (
                        <td className="px-3 py-2 text-right">
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={deleteMutation.isPending}
                            onClick={() => handleEliminar(v.id)}
                          >
                            Eliminar
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Sección 2 — Formulario de alta (solo si canWrite) */}
        {canWrite && (
          <>
            {/* Separador visual con etiqueta */}
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Agregar convenio
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>

            <div className="flex flex-col gap-3">
              {/* Select Convenio Específico vigente */}
              <div className="grid gap-1.5">
                <Label className="text-sm font-medium">
                  Convenio Específico vigente
                </Label>
                <EntityCombobox<number>
                  key={universidad ?? 0}
                  endpoint="conventions"
                  params={convenioParams}
                  toLabel={(r) =>
                    r.nomenclatura
                      ? `${String(r.nomenclatura)} — ${String(r.titulo ?? r.id)}`
                      : String(r.titulo ?? r.id)
                  }
                  value={convenioSeleccionado}
                  onChange={(v) => {
                    setConvenioSeleccionado(v);
                    setIpressSeleccionada(null); // resetear IPRESS al cambiar convenio
                  }}
                  disabled={universidad == null}
                  placeholder={
                    universidad == null
                      ? "Selecciona una universidad primero…"
                      : "Buscar convenio…"
                  }
                />
              </div>

              {/* Select IPRESS (sedes docentes) */}
              <div className="grid gap-1.5">
                <Label className="text-sm font-medium">IPRESS (sede docente)</Label>
                <EntityCombobox<string>
                  endpoint="ipress"
                  params={ipressParams}
                  valueKey="codigo_renipress"
                  toLabel={(r) => String(r.nombre ?? r.codigo_renipress ?? r.id)}
                  value={ipressSeleccionada}
                  onChange={setIpressSeleccionada}
                  disabled={convenioSeleccionado == null}
                  placeholder={
                    convenioSeleccionado == null
                      ? "Selecciona un convenio primero…"
                      : "Buscar IPRESS…"
                  }
                />
              </div>

              {/* Botón Agregar */}
              <div className="flex justify-end">
                <Button
                  onClick={handleAgregar}
                  disabled={
                    convenioSeleccionado == null ||
                    ipressSeleccionada == null ||
                    addMutation.isPending
                  }
                >
                  {addMutation.isPending ? "Agregando…" : "Agregar"}
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
