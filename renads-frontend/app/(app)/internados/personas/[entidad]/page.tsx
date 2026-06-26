"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { PERSON_CONFIGS } from "@/lib/internados/persons";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { Button } from "@/components/ui/button";

/** CRUD de una persona (interno/tutor), resuelta por el slug de la ruta. */
export default function PersonaPage() {
  const params = useParams<{ entidad: string }>();
  const config = PERSON_CONFIGS[params.entidad];

  if (!config) {
    return (
      <div className="grid gap-3">
        <p className="text-sm text-muted-foreground">Recurso no encontrado.</p>
        <Button
          variant="outline"
          render={<Link href="/internados/personas">Volver a personas</Link>}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/internados/personas"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Personas
        </Link>
      </div>
      <ResourceCrud config={config} />
    </div>
  );
}
