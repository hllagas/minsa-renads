"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { PERSON_CONFIGS } from "@/lib/internados/persons";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { useUniversityScope } from "@/lib/auth/scope";
import { hasAnnexes } from "@/lib/api/storage";
import type { RowAction } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { StudentsBulkUploadDialog } from "@/components/internados/students-bulk-upload-dialog";
import { AnnexChecklistAction } from "@/components/almacenamiento/annex-checklist-dialog";
import { Button } from "@/components/ui/button";

/** CRUD de una persona (estudiante/tutor), resuelta por el slug de la ruta. */
export default function PersonaPage() {
  const params = useParams<{ entidad: string }>();
  const config = PERSON_CONFIGS[params.entidad];
  const user = useAuthStore((s) => s.user);
  const { singleId } = useUniversityScope();

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

  // La carga masiva solo aplica a estudiantes y a los roles con escritura (gating UX).
  const canBulkUpload =
    params.entidad === "students" &&
    userHasRole(user, "Universidad", "Administrador RENADS");

  // Anexos (declaraciones juradas) — estudiantes, rol Universidad/Administrador RENADS.
  const entidad = params.entidad;
  const rowActions: RowAction<WithId>[] | undefined =
    hasAnnexes(entidad) && userHasRole(user, "Universidad", "Administrador RENADS")
      ? [
          {
            key: "anexos",
            label: "Anexos",
            render: (row) => <AnnexChecklistAction entidad={entidad} row={row} />,
            onClick: () => {},
          },
        ]
      : undefined;

  // Alcance: si el usuario tiene una sola universidad, se autocompleta y se oculta el selector
  // (en el alta y en el filtro) para estudiantes — no se pide lo que ya se conoce.
  const fixedValues =
    entidad === "students" && singleId != null ? { universidad: singleId } : undefined;

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
      <ResourceCrud
        config={config}
        rowActions={rowActions}
        headerActions={canBulkUpload ? <StudentsBulkUploadDialog /> : undefined}
        fixedValues={fixedValues}
      />
    </div>
  );
}
