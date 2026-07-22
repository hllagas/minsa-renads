"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { ENTITY_CONFIGS } from "@/lib/convenios/entities";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { hasLogo } from "@/lib/api/storage";
import type { RowAction } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { LogoUploadAction } from "@/components/catalogos/logo-upload-dialog";
import { Button } from "@/components/ui/button";

/** CRUD de una entidad maestra, resuelta por el slug de la ruta. */
export default function EntidadMaestraPage() {
  const params = useParams<{ entidad: string }>();
  const config = ENTITY_CONFIGS[params.entidad];
  const user = useAuthStore((s) => s.user);
  const entidad = params.entidad;

  // Universidades gestiona su logo dentro del formulario de edición (no como acción por fila).
  const rowActions: RowAction<WithId>[] | undefined =
    hasLogo(entidad) &&
    entidad !== "universities" &&
    userHasRole(user, "Administrador RENADS")
      ? [
          {
            key: "logo",
            label: "Logo",
            render: (row) => <LogoUploadAction entidad={entidad} row={row} />,
            onClick: () => {},
          },
        ]
      : undefined;

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
      <ResourceCrud config={config} rowActions={rowActions} />
    </div>
  );
}
