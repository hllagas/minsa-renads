"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import { LOGO_ACCEPT, MAX_UPLOAD_BYTES, useUploadLogo } from "@/lib/api/storage";
import { extractApiError } from "@/lib/api/errors";
import type { WithId } from "@/lib/api/query";
import { EntityLogo } from "@/components/ui/entity-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/**
 * Acción por fila «Logo»: previsualiza el logo actual (o su fallback) y sube/reemplaza uno nuevo
 * (`POST {entidad}/{id}/upload-logo/`). Solo imágenes PNG/JPEG/WEBP ≤ 25 MiB. El gating de rol
 * (`Administrador RENADS`) vive en la página; el backend es la autoridad final.
 */
export function LogoUploadAction({ entidad, row }: { entidad: string; row: WithId }) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadM = useUploadLogo(entidad, row.id);
  const referencia = (row.referencia_logo as string | undefined) ?? null;
  const nombre = (row.nombre as string | undefined) ?? `#${row.id}`;

  function reset() {
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next) reset();
  }

  function onSubmit() {
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      toast.error("El archivo supera el tamaño máximo permitido (25 MiB).");
      return;
    }
    uploadM.mutate(file, {
      onSuccess: () => {
        toast.success("Logo actualizado.");
        onOpenChange(false);
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm">
            Logo
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Logo — {nombre}</DialogTitle>
          <DialogDescription>
            Imagen PNG, JPEG o WEBP (máx. 25 MiB). Reemplaza el logo actual.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-4">
          <EntityLogo entidad={entidad} id={row.id} referenciaLogo={referencia} size={96} />
          <div className="grid flex-1 gap-2">
            <Label htmlFor="logo-file">Nuevo logo</Label>
            <Input
              id="logo-file"
              ref={inputRef}
              type="file"
              accept={LOGO_ACCEPT}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={uploadM.isPending}
            />
          </div>
        </div>

        <DialogFooter>
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
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
