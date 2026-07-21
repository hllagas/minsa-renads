"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { CATALOGO_ENTITY_CONFIGS } from "@/lib/catalogos/entities";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { hasAnnexes, hasLogo } from "@/lib/api/storage";
import type { RowAction } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { IpressSedeDocenteAction } from "@/components/catalogos/ipress-sede-docente-action";
import { LogoUploadAction } from "@/components/catalogos/logo-upload-dialog";
import { AnnexChecklistAction } from "@/components/almacenamiento/annex-checklist-dialog";
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

  const entidad = params.entidad;
  const actions: RowAction<WithId>[] = [];

  // Logo (subir/reemplazar) — 5 entidades con logo, solo `Administrador RENADS`.
  if (hasLogo(entidad) && userHasRole(user, "Administrador RENADS")) {
    actions.push({
      key: "logo",
      label: "Logo",
      render: (row) => <LogoUploadAction entidad={entidad} row={row} />,
      onClick: () => {},
    });
  }

  // Anexos (declaraciones juradas por actor) — solo `Administrador RENADS` en /catalogos.
  if (hasAnnexes(entidad) && userHasRole(user, "Administrador RENADS")) {
    actions.push({
      key: "anexos",
      label: "Anexos",
      render: (row) => <AnnexChecklistAction entidad={entidad} row={row} />,
      onClick: () => {},
    });
  }

  // La acción «sede docente» vive solo en /catalogos/entidades/ipress y solo para CONAPRES.
  if (entidad === "ipress" && userHasRole(user, "CONAPRES")) {
    actions.push({
      key: "sede-docente",
      label: "Sede docente",
      render: (row) => <IpressSedeDocenteAction row={row} />,
      onClick: () => {},
    });
  }

  const rowActions = actions.length ? actions : undefined;

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
