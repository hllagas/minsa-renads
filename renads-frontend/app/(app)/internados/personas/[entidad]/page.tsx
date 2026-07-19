"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { PERSON_CONFIGS } from "@/lib/internados/persons";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { StudentsBulkUploadDialog } from "@/components/internados/students-bulk-upload-dialog";
import { Button } from "@/components/ui/button";

/** CRUD de una persona (estudiante/tutor), resuelta por el slug de la ruta. */
export default function PersonaPage() {
  const params = useParams<{ entidad: string }>();
  const config = PERSON_CONFIGS[params.entidad];
  const user = useAuthStore((s) => s.user);

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
        headerActions={canBulkUpload ? <StudentsBulkUploadDialog /> : undefined}
      />
    </div>
  );
}
