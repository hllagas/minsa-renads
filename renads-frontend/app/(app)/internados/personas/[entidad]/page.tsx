"use client";

import { useMemo, useState } from "react";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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
 * Vista de estudiantes: elegir universidad (acotada al alcance) → elegir nivel académico (default
 * «Pregrado») → listar/gestionar. La universidad se fija (oculta) en el form y filtra el listado. El
 * **nivel elegido aquí** filtra el listado y se hereda en el form (que ya no pregunta el nivel:
 * muestra carrera si es Pregrado, especialidad en otro nivel).
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
  const niveles = useMemo(() => nivelesQuery.data ?? [], [nivelesQuery.data]);
  const pregradoId = useMemo<number | null>(() => {
    const p = niveles.find((l) =>
      String(l.nombre ?? "").toLowerCase().includes("pregrado"),
    );
    return p ? Number(p.id) : null;
  }, [niveles]);

  // Nivel activo de la vista: el elegido por el usuario o, por defecto, «Pregrado» (derivado — sin
  // efecto/setState) en cuanto se resuelve el catálogo.
  const [nivelPicked, setNivelPicked] = useState<number | null>(null);
  const nivel = nivelPicked ?? pregradoId;

  const config = useMemo(() => buildStudentsConfig(nivel, pregradoId), [nivel, pregradoId]);
  const initialFilters = useMemo<Record<string, string> | undefined>(
    () => (nivel != null ? { nivel_academico: String(nivel) } : undefined),
    [nivel],
  );

  return (
    <div>
      <BackLink />
      <div className="mb-4 flex flex-wrap items-end gap-4">
        {gateUI}
        {universidad != null ? (
          <div className="grid gap-1.5 max-w-xs">
            <Label className="text-sm font-medium">Nivel académico</Label>
            <Select
              value={nivel != null ? String(nivel) : ""}
              onValueChange={(v) => setNivelPicked(v ? Number(v) : null)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Selecciona un nivel…" />
              </SelectTrigger>
              <SelectContent>
                {niveles.map((l) => (
                  <SelectItem key={String(l.id)} value={String(l.id)}>
                    {String(l.nombre ?? l.id)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ) : null}
      </div>
      {universidad == null ? (
        <EmptyPick label="Selecciona una universidad para ver sus estudiantes." />
      ) : (
        <ResourceCrud
          key={`${universidad}-${nivel ?? "x"}`}
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
