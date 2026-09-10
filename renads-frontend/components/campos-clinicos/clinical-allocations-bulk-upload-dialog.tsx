"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import {
  useClinicalAllocationsBulkUpload,
  type ClinicalBulkUploadResult,
} from "@/lib/campos-clinicos/hooks";
import { extractApiError } from "@/lib/api/errors";
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

/** Carga masiva de asignaciones de campos clínicos (sede docente + carrera profesional + universidad). */
export function ClinicalAllocationsBulkUploadDialog() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ClinicalBulkUploadResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadM = useClinicalAllocationsBulkUpload();

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
    uploadM.mutate(file, {
      onSuccess: (data) => {
        setResult(data);
        toast.success(
          `Carga procesada: ${data.creados} creado(s), ${data.omitidos} omitido(s).`,
        );
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger render={<Button variant="outline">Carga masiva</Button>} />
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Carga masiva — Asignación de campos clínicos</DialogTitle>
          <DialogDescription>
            Sube un archivo <strong>.xlsx</strong> con las asignaciones por sede docente, carrera
            profesional y universidad. Columnas requeridas:{" "}
            <code>campo_clinico_ipress</code> (id del registro de determinación),{" "}
            <code>convenio</code> (id del convenio Específico),{" "}
            <code>universidad</code> (id),{" "}
            <code>campos_clinicos_autorizados</code> (número),{" "}
            <code>fecha_inicio</code> y <code>fecha_fin</code> (AAAA-MM-DD). Filas con error
            se omiten sin abortar el lote.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2">
          <Label htmlFor="allocations-bulk-file">Archivo (.xlsx) *</Label>
          <Input
            id="allocations-bulk-file"
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
                <p className="text-sm text-muted-foreground">Filas omitidas:</p>
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
