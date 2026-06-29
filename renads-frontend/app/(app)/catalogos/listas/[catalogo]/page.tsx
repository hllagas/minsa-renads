"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { CATALOG_CONFIGS } from "@/lib/catalogos/catalogs";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { Button } from "@/components/ui/button";

/** Vista de solo lectura de un catálogo (o `ubigeos`), resuelto por el slug de la ruta. */
export default function CatalogoListaPage() {
  const params = useParams<{ catalogo: string }>();
  const config = CATALOG_CONFIGS[params.catalogo];

  if (!config) {
    return (
      <div className="grid gap-3">
        <p className="text-sm text-muted-foreground">Catálogo no encontrado.</p>
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
