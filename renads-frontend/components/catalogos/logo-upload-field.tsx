"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { ImageUp, Loader2 } from "lucide-react";

import { LOGO_ACCEPT, MAX_UPLOAD_BYTES, useUploadLogo } from "@/lib/api/storage";
import { extractApiError } from "@/lib/api/errors";
import { EntityLogo } from "@/components/ui/entity-logo";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";

/**
 * Uploader de logo **embebido en el formulario de edición** (no un diálogo aparte): previsualiza
 * el logo actual (o su fallback) y sube/reemplaza uno nuevo (`POST {entidad}/{id}/upload-logo/`).
 * Se monta vía `ResourceConfig.renderEditInfo`, por lo que solo aparece al editar (ya existe `id`);
 * en el alta, primero se guarda el registro y luego se edita para añadir el logo.
 */
export function LogoUploadField({
  entidad,
  id,
  referenciaLogo,
}: {
  entidad: string;
  id: number;
  referenciaLogo?: string | null;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [localRef, setLocalRef] = useState<string | null>(referenciaLogo ?? null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uploadM = useUploadLogo(entidad, id);

  function onSubmit() {
    if (!file) return;
    if (file.size > MAX_UPLOAD_BYTES) {
      toast.error("El archivo supera el tamaño máximo permitido (25 MiB).");
      return;
    }
    uploadM.mutate(file, {
      onSuccess: (data) => {
        setLocalRef(data.referencia_logo);
        toast.success("Logo actualizado.");
        setFile(null);
        if (inputRef.current) inputRef.current.value = "";
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  return (
    <div className="flex items-center gap-4">
      <EntityLogo
        entidad={entidad}
        id={id}
        referenciaLogo={localRef}
        size={72}
      />
      <div className="grid flex-1 gap-2">
        <Label>Logo (PNG, JPEG o WEBP · máx. 25 MiB)</Label>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept={LOGO_ACCEPT}
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            disabled={uploadM.isPending}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => inputRef.current?.click()}
            disabled={uploadM.isPending}
          >
            <ImageUp /> Seleccionar
          </Button>
          {file ? (
            <span
              className="max-w-40 truncate text-xs text-muted-foreground"
              title={file.name}
            >
              {file.name}
            </span>
          ) : null}
          <Button
            type="button"
            size="sm"
            onClick={onSubmit}
            disabled={!file || uploadM.isPending}
          >
            {uploadM.isPending ? <Loader2 className="animate-spin" /> : "Subir"}
          </Button>
        </div>
      </div>
    </div>
  );
}
