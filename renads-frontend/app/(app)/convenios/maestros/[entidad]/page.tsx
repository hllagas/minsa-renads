"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { ENTITY_CONFIGS } from "@/lib/convenios/entities";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { Button } from "@/components/ui/button";

/** CRUD de una entidad maestra, resuelta por el slug de la ruta. */
export default function EntidadMaestraPage() {
  const params = useParams<{ entidad: string }>();
  const config = ENTITY_CONFIGS[params.entidad];

  if (!config) {
    return (
      <div className="grid gap-3">
        <p className="text-sm text-muted-foreground">Entidad no encontrada.</p>
        <Button
          variant="outline"
          render={<Link href="/convenios/maestros">Volver a maestros</Link>}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/convenios/maestros"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Maestros
        </Link>
      </div>
      <ResourceCrud config={config} />
    </div>
  );
}
