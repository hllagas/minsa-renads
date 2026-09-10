"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import {
  useClinicalRegistrationsBulkUpload,
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

/** Carga masiva de determinaciones de campos de formación (sede docente + carrera profesional). */
export function ClinicalRegistrationsBulkUploadDialog() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ClinicalBulkUploadResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadM = useClinicalRegistrationsBulkUpload();

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
          <DialogTitle>Carga masiva — Determinación de campos de formación</DialogTitle>
          <DialogDescription>
            Sube un archivo <strong>.xlsx</strong> con las determinaciones por sede docente y
            profesión. Columnas requeridas:{" "}
            <code>ipress</code> (código RENIPRESS),{" "}
            <code>carrera_profesional</code> (id o nombre),{" "}
            <code>campos_clinicos_registrados</code> (número).
            Columnas opcionales: <code>convenio</code> (id), <code>especialidad</code> (id),{" "}
            <code>numero_resolucion_conapres</code>, <code>fecha_resolucion_conapres</code>{" "}
            (AAAA-MM-DD). Filas con error se omiten sin abortar el lote.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2">
          <Label htmlFor="registrations-bulk-file">Archivo (.xlsx) *</Label>
          <Input
            id="registrations-bulk-file"
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
