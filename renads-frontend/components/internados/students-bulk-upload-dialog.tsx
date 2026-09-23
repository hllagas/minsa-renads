"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import {
  useStudentsBulkUpload,
  useStudentsBulkValidate,
} from "@/lib/internados/hooks";
import { extractApiError } from "@/lib/api/errors";
import { DownloadIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/** Dispara la descarga de un `Blob` (la trama `.xlsx` anotada con las celdas a corregir). */
function descargarBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Diálogo de carga masiva de estudiantes (RN-16). Sube un `.xlsx` y muestra el resumen del
 * backend (`creados`/`omitidos`) más la tabla de errores por fila (las filas inválidas se omiten
 * sin abortar el lote). El gating de rol vive en la página; el backend es la autoridad final.
 *
 * Recibe `universidadId` y `periodoId` del contexto de la vista (filtros ya seleccionados),
 * y los envía como parámetros de formulario al endpoint de carga masiva.
 */
export function StudentsBulkUploadDialog({
  scoped,
  universidadId,
  esPregrado = true,
  periodoId,
}: {
  /** `true` si el usuario está acotado a universidades concretas (backend valida por fila). */
  scoped?: boolean;
  /** ID de la universidad seleccionada en el filtro de la vista principal. */
  universidadId?: number | null;
  /** `true` cuando el nivel activo es PREGRADO (determina la trama a descargar). */
  esPregrado?: boolean;
  /** ID del periodo de internado activo (solo aplica a nivel PREGRADO). */
  periodoId?: number | null;
} = {}) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<{ creados?: number; errores?: number } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const validateM = useStudentsBulkValidate();
  const uploadM = useStudentsBulkUpload();
  const pending = validateM.isPending || uploadM.isPending;

  const tramaNombre = esPregrado
    ? "TramaCargaMasivaEstudiantes_PREGRADO.xlsx"
    : "TramaCargaMasivaEstudiantes_noPREGRADO.xlsx";
  const tramaLabel = esPregrado ? "Trama Pregrado" : "Trama Posgrado / Especialidad";

  function reset() {
    setFile(null);
    setResult(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next) reset();
  }

  function onSubmit() {
    if (!file) return;
    const params = { archivo: file, universidadId, periodoId: esPregrado ? periodoId : null };
    // Paso 1: pre-validar. Si hay inconsistencias, el backend devuelve la trama anotada.
    validateM.mutate(params, {
      onSuccess: (r) => {
        if (!r.valido) {
          descargarBlob(r.blob, r.filename);
          setResult({ errores: r.errores });
          toast.error(
            `Se encontraron inconsistencias en ${r.errores} fila(s). Descargamos la trama con las ` +
              `celdas resaltadas para que las corrijas y la vuelvas a subir.`,
          );
          return;
        }
        // Paso 2: trama limpia → crear todo (all-or-nothing).
        uploadM.mutate(params, {
          onSuccess: (data) => {
            setResult({ creados: data.creados });
            toast.success(`Carga completada: ${data.creados} estudiante(s) creado(s).`);
          },
          onError: (e) => toast.error(extractApiError(e)),
        });
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger render={<Button variant="outline">Carga masiva</Button>} />
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Carga masiva de estudiantes</DialogTitle>
          <DialogDescription>
            Sube un archivo <strong>.xlsx</strong> con la estructura de la trama oficial. La
            universidad y el periodo se toman automáticamente de los filtros activos. Primero se
            <strong> valida</strong> toda la trama: si hay inconsistencias se descarga el archivo
            con las <strong>celdas resaltadas</strong> y no se crea nada; solo si está limpia se
            cargan todos los estudiantes.
          </DialogDescription>
        </DialogHeader>

        {/* ── Descargar formato ── */}
        <div className="rounded-md border bg-muted/40 p-4">
          <p className="mb-3 text-sm font-medium">
            1. Descarga la trama para el nivel activo
          </p>
          <a href={`/${tramaNombre}`} download className="inline-flex">
            <Button type="button" variant="outline" size="sm" className="gap-2">
              <DownloadIcon className="h-4 w-4" />
              {tramaLabel}
            </Button>
          </a>
        </div>

        <hr className="border-border" />

        {scoped ? (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
            Tu acceso está acotado a tus universidades autorizadas. Las filas cuya
            <code> universidad_id</code> esté fuera de tu alcance serán <strong>rechazadas</strong>
            por el sistema (validación por fila).
          </div>
        ) : null}

        <div className="grid gap-2">
          <p className="text-sm font-medium">2. Completa la trama y súbela aquí</p>
          <Label htmlFor="students-bulk-file">Archivo (.xlsx) *</Label>
          <Input
            id="students-bulk-file"
            ref={inputRef}
            type="file"
            accept=".xlsx"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setResult(null);
            }}
            disabled={pending}
          />
        </div>

        {result ? (
          result.creados != null ? (
            <div className="flex items-center gap-2">
              <Badge>Creados: {result.creados}</Badge>
            </div>
          ) : (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
              Se encontraron inconsistencias en <strong>{result.errores}</strong> fila(s). Se
              descargó la trama con las <strong>celdas resaltadas en rojo</strong> y el motivo en
              el comentario de cada celda. Corrígelas y vuelve a subir el archivo. No se creó
              ningún estudiante.
            </div>
          )
        ) : null}

        <DialogFooter>
          {result ? (
            <>
              <Button variant="outline" onClick={reset}>
                Subir otro archivo
              </Button>
              <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={pending}
              >
                Cancelar
              </Button>
              <Button onClick={onSubmit} disabled={!file || pending}>
                {validateM.isPending ? "Validando…" : uploadM.isPending ? "Subiendo…" : "Subir"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
