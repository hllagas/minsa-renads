"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, XCircle, Paperclip, Upload, Loader2 } from "lucide-react";

import {
  ANNEX_ACCEPT,
  MAX_UPLOAD_BYTES,
  useAnnexChecklist,
  useUploadAnnex,
  type AnnexChecklistItem,
} from "@/lib/api/storage";
import { extractApiError } from "@/lib/api/errors";
import type { WithId } from "@/lib/api/query";
import { Button } from "@/components/ui/button";
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

/** Fila del checklist: estado del anexo + subida de su PDF (nueva versión al re-subir). */
function AnnexRow({
  entidad,
  id,
  item,
}: {
  entidad: string;
  id: number;
  item: AnnexChecklistItem;
}) {
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadM = useUploadAnnex(entidad, id);

  function onSubmit() {
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      toast.error("El archivo supera el tamaño máximo permitido (25 MiB).");
      return;
    }
    uploadM.mutate(
      { documento_anexo: item.documento_anexo, archivo: file, nombre_archivo: file.name },
      {
        onSuccess: (doc) => {
          toast.success(`${item.nombre}: adjuntado (v${doc.version}).`);
          setFile(null);
          if (inputRef.current) inputRef.current.value = "";
        },
        onError: (e) => toast.error(extractApiError(e)),
      },
    );
  }

  const pendiente = item.obligatorio && !item.adjuntado;

  return (
    <TableRow className={pendiente ? "bg-destructive/5" : undefined}>
      <TableCell>
        <div className="grid gap-0.5">
          <span className="font-medium">{item.nombre}</span>
          <span className="text-xs text-muted-foreground">{item.codigo}</span>
        </div>
      </TableCell>
      <TableCell>
        {item.adjuntado ? (
          <span
            className="inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400"
            title={`Adjuntado${item.version ? ` · v${item.version}` : ""}`}
          >
            <CheckCircle2 className="size-5" aria-label="Adjuntado" />
            {item.version ? (
              <span className="text-xs text-muted-foreground">v{item.version}</span>
            ) : null}
          </span>
        ) : (
          <span
            className="inline-flex items-center text-destructive"
            title={item.obligatorio ? "Faltante (obligatorio)" : "Faltante"}
          >
            <XCircle className="size-5" aria-label="Faltante" />
          </span>
        )}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept={ANNEX_ACCEPT}
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            disabled={uploadM.isPending}
          />
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Seleccionar archivo"
            title="Seleccionar archivo (PDF)"
            disabled={uploadM.isPending}
            onClick={() => inputRef.current?.click()}
          >
            <Paperclip />
          </Button>
          {file ? (
            <span
              className="max-w-32 truncate text-xs text-muted-foreground"
              title={file.name}
            >
              {file.name}
            </span>
          ) : null}
          <Button
            size="icon-sm"
            aria-label={item.adjuntado ? "Reemplazar" : "Subir"}
            title={item.adjuntado ? "Reemplazar" : "Subir"}
            onClick={onSubmit}
            disabled={!file || uploadM.isPending}
          >
            {uploadM.isPending ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Upload />
            )}
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

/**
 * Acción por fila «Anexos»: checklist de declaraciones juradas del actor
 * (`GET {entidad}/{id}/annex-checklist/`) con subida por ítem (`POST .../annex-upload/`, PDF).
 * El checklist solo se pide al abrir. El gating de rol vive en la página.
 */
export function AnnexChecklistAction({ entidad, row }: { entidad: string; row: WithId }) {
  const [open, setOpen] = useState(false);
  const checklist = useAnnexChecklist(entidad, row.id, open);
  const nombre =
    [row.nombres, row.apellido_paterno].filter(Boolean).join(" ") ||
    (row.estudiante as string | undefined) ||
    (row.nombre as string | undefined) ||
    `#${row.id}`;

  const items = checklist.data ?? [];
  const faltan = items.filter((i) => i.obligatorio && !i.adjuntado).length;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm">
            Anexos
          </Button>
        }
      />
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Anexos — {nombre}</DialogTitle>
          <DialogDescription>
            Declaraciones juradas requeridas (PDF, máx. 25 MiB). Re-subir un anexo genera una nueva
            versión.
          </DialogDescription>
        </DialogHeader>

        {checklist.isLoading ? (
          <p className="text-sm text-muted-foreground">Cargando checklist…</p>
        ) : checklist.isError ? (
          <div className="flex items-center gap-3">
            <p className="text-sm text-destructive">No se pudo cargar el checklist.</p>
            <Button variant="outline" size="sm" onClick={() => checklist.refetch()}>
              Reintentar
            </Button>
          </div>
        ) : items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Este actor no requiere anexos.
          </p>
        ) : (
          <>
            {faltan > 0 ? (
              <p className="text-sm text-destructive">
                Faltan {faltan} anexo(s) obligatorio(s).
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                Todos los anexos obligatorios están adjuntados.
              </p>
            )}
            <div className="max-h-96 overflow-y-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Anexo</TableHead>
                    <TableHead className="w-24">Estado</TableHead>
                    <TableHead>Archivo</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <AnnexRow
                      key={item.documento_anexo}
                      entidad={entidad}
                      id={row.id}
                      item={item}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
