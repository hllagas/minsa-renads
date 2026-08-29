"use client";

import { useState } from "react";
import { Building2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { useLogoUrl } from "@/lib/api/storage";

/**
 * Logo de una entidad con **fallback institucional** (ícono `Building2`).
 * - Sin `referenciaLogo` → no pide la URL (evita `404`) y muestra el fallback directo.
 * - Con referencia → pide el signed URL (`logo-url`) bajo demanda y lo renderiza; si falla la
 *   petición o la imagen (`onError`), cae al fallback.
 *
 * Usa `<img>` (no `next/image`) porque el signed URL es de host remoto y de corta duración: evita
 * configurar `remotePatterns` y el caché de optimización de Next para una URL que caduca.
 */
export function EntityLogo({
  entidad,
  id,
  referenciaLogo,
  size = 40,
  className,
  alt,
}: {
  entidad: string;
  id: number;
  referenciaLogo?: string | null;
  size?: number;
  className?: string;
  alt?: string;
}) {
  const hasRef = Boolean(referenciaLogo);
  const { data, isError } = useLogoUrl(entidad, id, hasRef);
  // Guarda la URL que falló al cargar; al cambiar la URL (p. ej. tras subir un logo nuevo) el
  // fallback se descarta solo, sin necesidad de un efecto.
  const [erroredUrl, setErroredUrl] = useState<string | null>(null);
  const url = data?.url;

  const showFallback = !hasRef || isError || !url || erroredUrl === url;
  const label = alt ?? "Logo de la entidad";

  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center overflow-hidden rounded-md border bg-muted",
        className,
      )}
      style={{ width: size, height: size }}
    >
      {showFallback ? (
        <Building2
          className="text-muted-foreground"
          style={{ width: size * 0.5, height: size * 0.5 }}
          aria-label={label}
        />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt={label}
          className="h-full w-full object-contain"
          onError={() => setErroredUrl(url ?? null)}
        />
      )}
    </div>
  );
}
