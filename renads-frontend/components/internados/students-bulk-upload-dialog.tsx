"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import {
  useStudentsBulkUpload,
  type StudentBulkUploadResult,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
  const [result, setResult] = useState<StudentBulkUploadResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadM = useStudentsBulkUpload();

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
    uploadM.mutate(
      { archivo: file, universidadId, periodoId: esPregrado ? periodoId : null },
      {
        onSuccess: (data) => {
          setResult(data);
          toast.success(
            `Carga procesada: ${data.creados} creado(s), ${data.omitidos} omitido(s).`,
          );
        },
        onError: (e) => toast.error(extractApiError(e)),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger render={<Button variant="outline">Carga masiva</Button>} />
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Carga masiva de estudiantes</DialogTitle>
          <DialogDescription>
            Sube un archivo <strong>.xlsx</strong> con la estructura de la trama oficial.
            Columnas requeridas: <code>tipo_documento</code> (DNI / CE / PASAPORTE),{" "}
            <code>numero_documento</code>, <code>nombres</code>, <code>apellido_paterno</code> y{" "}
            {esPregrado
              ? <><code>carrera_profesional</code> (nombre exacto)</>
              : <><code>especialidad</code> (nombre exacto)</>
            }.
            La universidad y el periodo se toman automáticamente de los filtros activos.
            Las filas con error se omiten sin abortar el resto del lote.
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
            disabled={uploadM.isPending}
          />
        </div>

        {result ? (
          <div className="grid gap-3">
            <div className="flex items-center gap-2">
              <Badge>Creados: {result.creados}</Badge>
              <Badge variant="secondary">Omitidos: {result.omitidos}</Badge>
            </div>
            {result.errores.length > 0 ? (
              <div className="grid gap-2">
                <p className="text-sm text-muted-foreground">
                  Las siguientes filas se omitieron:
                </p>
                <div className="max-h-64 overflow-y-auto rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-20">Fila</TableHead>
                        <TableHead>Motivo</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.errores.map((err, i) => (
                        <TableRow key={`${err.fila}-${i}`}>
                          <TableCell>{err.fila}</TableCell>
                          <TableCell>{err.motivo}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            ) : null}
          </div>
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
                disabled={uploadM.isPending}
              >
                Cancelar
              </Button>
              <Button onClick={onSubmit} disabled={!file || uploadM.isPending}>
                {uploadM.isPending ? "Subiendo…" : "Subir"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
