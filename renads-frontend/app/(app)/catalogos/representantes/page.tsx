"use client";

import Link from "next/link";

import { REPRESENTATIVES_CONFIG } from "@/lib/catalogos/representatives";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import type { RowAction } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { AnnexChecklistAction } from "@/components/almacenamiento/annex-checklist-dialog";

/** Representantes (CRUD polimórfico) — v1: list + filtros + editar + eliminar (alta diferida a v2). */
export default function RepresentantesPage() {
  const user = useAuthStore((s) => s.user);

  // Anexos (declaraciones juradas del representante) — solo `Administrador RENADS`.
  const rowActions: RowAction<WithId>[] | undefined = userHasRole(user, "Administrador RENADS")
    ? [
        {
          key: "anexos",
          label: "Anexos",
          render: (row) => <AnnexChecklistAction entidad="representatives" row={row} />,
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
      <ResourceCrud config={REPRESENTATIVES_CONFIG} rowActions={rowActions} />
    </div>
  );
}
