"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { PERSON_CONFIGS, buildStudentsConfig } from "@/lib/internados/persons";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { useUniversityScope } from "@/lib/auth/scope";
import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { StudentsBulkUploadDialog } from "@/components/internados/students-bulk-upload-dialog";
import { useUniversityGate } from "@/components/internados/university-gate";
import { Button } from "@/components/ui/button";

/** CRUD de una persona (estudiante/tutor), resuelta por el slug de la ruta. */
export default function PersonaPage() {
  const params = useParams<{ entidad: string }>();
  const entidad = params.entidad;

  if (entidad === "students") return <StudentsView />;
  if (entidad === "tutors") return <TutorsView />;

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

function BackLink() {
  return (
    <div className="mb-4">
      <Link href="/internados" className="text-sm text-muted-foreground hover:text-foreground">
        ← Internados
      </Link>
    </div>
  );
}

function EmptyPick({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
    </div>
  );
}

/**
 * Vista de estudiantes: elegir universidad (acotada al alcance) → listar/gestionar. La universidad
 * se fija (oculta) en el form y filtra el listado. El filtro de nivel arranca en «Pregrado».
 */
function StudentsView() {
  const user = useAuthStore((s) => s.user);
  const { universidad, gateUI } = useUniversityGate();
  const { scoped } = useUniversityScope();
  const canBulkUpload = userHasRole(user, "Universidad", "Administrador RENADS");

  const nivelesQuery = useQuery({
    queryKey: ["academic-levels", "for-students"],
    queryFn: () =>
      api.get<Paginated<WithId>>("/academic-levels/").then((r) => r.data.results),
    staleTime: 10 * 60_000,
  });
  const pregradoId = useMemo<number | null>(() => {
    const p = (nivelesQuery.data ?? []).find((l) =>
      String(l.nombre ?? "").toLowerCase().includes("pregrado"),
    );
    return p ? Number(p.id) : null;
  }, [nivelesQuery.data]);

  const config = useMemo(() => buildStudentsConfig(pregradoId), [pregradoId]);
  const initialFilters = useMemo<Record<string, string> | undefined>(
    () => (pregradoId != null ? { nivel_academico: String(pregradoId) } : undefined),
    [pregradoId],
  );

  return (
    <div>
      <BackLink />
      <div className="mb-4">{gateUI}</div>
      {universidad == null ? (
        <EmptyPick label="Selecciona una universidad para ver sus estudiantes." />
      ) : (
        <ResourceCrud
          key={`${universidad}-${pregradoId ?? "x"}`}
          config={config}
          fixedValues={{ universidad }}
          initialFilters={initialFilters}
          headerActions={
            canBulkUpload ? <StudentsBulkUploadDialog scoped={scoped} /> : undefined
          }
        />
      )}
    </div>
  );
}

/**
 * Vista de tutores: elegir universidad (acotada al alcance) → listar los tutores de esa universidad
 * (filtro `universidades`). No usa `fixedValues` porque `universidades` es M2M (1–2, RN-24).
 */
function TutorsView() {
  const { universidad, gateUI } = useUniversityGate();
  const config = PERSON_CONFIGS.tutors;
  const initialFilters = useMemo<Record<string, string> | undefined>(
    () => (universidad != null ? { universidades: String(universidad) } : undefined),
    [universidad],
  );

  return (
    <div>
      <BackLink />
      <div className="mb-4">{gateUI}</div>
      {universidad == null ? (
        <EmptyPick label="Selecciona una universidad para ver sus tutores." />
      ) : (
        <ResourceCrud key={universidad} config={config} initialFilters={initialFilters} />
      )}
    </div>
  );
}
