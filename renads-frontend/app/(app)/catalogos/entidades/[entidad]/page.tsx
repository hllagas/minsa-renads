"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { CATALOGO_ENTITY_CONFIGS } from "@/lib/catalogos/entities";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import type { RowAction } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { IpressSedeDocenteAction } from "@/components/catalogos/ipress-sede-docente-action";
import { Button } from "@/components/ui/button";

/** CRUD de una entidad organizacional/académica, resuelta por el slug de la ruta. */
export default function EntidadCatalogoPage() {
  const params = useParams<{ entidad: string }>();
  const config = CATALOGO_ENTITY_CONFIGS[params.entidad];
  const user = useAuthStore((s) => s.user);

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

  // La acción «sede docente» vive solo en /catalogos/entidades/ipress y solo para CONAPRES.
  const rowActions: RowAction<WithId>[] | undefined =
    params.entidad === "ipress" && userHasRole(user, "CONAPRES")
      ? [
          {
            key: "sede-docente",
            label: "Sede docente",
            render: (row) => <IpressSedeDocenteAction row={row} />,
            onClick: () => {},
          },
        ]
      : undefined;

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
      <ResourceCrud config={config} rowActions={rowActions} />
    </div>
  );
}
