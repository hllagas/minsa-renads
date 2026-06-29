"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { CATALOGO_ENTITY_CONFIGS } from "@/lib/catalogos/entities";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { Button } from "@/components/ui/button";

/** CRUD de una entidad organizacional/académica, resuelta por el slug de la ruta. */
export default function EntidadCatalogoPage() {
  const params = useParams<{ entidad: string }>();
  const config = CATALOGO_ENTITY_CONFIGS[params.entidad];

  if (!config) {
    return (
      <div className="grid gap-3">
        <p className="text-sm text-muted-foreground">Entidad no encontrada.</p>
        <Button
          variant="outline"
          render={<Link href="/catalogos">Volver a catálogos</Link>}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/catalogos"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Catálogos
        </Link>
      </div>
      <ResourceCrud config={config} />
    </div>
  );
}
