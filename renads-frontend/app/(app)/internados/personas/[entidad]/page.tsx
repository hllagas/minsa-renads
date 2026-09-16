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
import { PageHeader } from "@/components/data/page-header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
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
 * El filtro de periodo de internado (solo Pregrado) se precarga con el último periodo activo.
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

  // Nivel activo de la vista: el elegido por el usuario o, por defecto, «Pregrado».
  const [nivelPicked, setNivelPicked] = useState<number | null>(null);
  const nivel = nivelPicked ?? pregradoId;
  const esPregrado = nivel != null && nivel === pregradoId;

  // Último periodo de internado activo (default del filtro de periodo).
  const periodosQuery = useQuery({
    queryKey: ["internship-periods", "activos"],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/internship-periods/", { params: { activo: "true", ordering: "-id", page_size: "1" } })
        .then((r) => r.data.results),
    staleTime: 10 * 60_000,
  });
  const lastActivoPeriodoId = useMemo<number | null>(() => {
    const p = periodosQuery.data?.[0];
    return p ? Number(p.id) : null;
  }, [periodosQuery.data]);
  const periodos = useMemo(() => periodosQuery.data ?? [], [periodosQuery.data]);

  const [periodoPicked, setPeriodoPicked] = useState<number | null>(null);
  const periodoId = periodoPicked !== null ? periodoPicked : lastActivoPeriodoId;

  const config = useMemo(() => buildStudentsConfig(nivel, pregradoId), [nivel, pregradoId]);
  const initialFilters = useMemo<Record<string, string>>(() => {
    const f: Record<string, string> = {};
    if (nivel != null) f.nivel_academico = String(nivel);
    if (periodoId != null && esPregrado) f.periodo_internado = String(periodoId);
    return f;
  }, [nivel, periodoId, esPregrado]);

  return (
    <div>
      <BackLink />
      <PageHeader title="Estudiantes" description="Estudiantes en proceso de internado." />
      <div className="mb-4 flex flex-wrap items-end gap-4">
        {gateUI}
        {universidad != null ? (
          <>
            <div className="grid gap-1.5 max-w-xs">
              <Label className="text-sm font-medium">Nivel académico</Label>
              <Select
                value={nivel != null ? String(nivel) : ""}
                onValueChange={(v) => {
                  setNivelPicked(v ? Number(v) : null);
                  setPeriodoPicked(null);
                }}
              >
                <SelectTrigger className="w-full">
                  {/*
                    Radix lazy-renders SelectContent (solo al abrir) → SelectValue nunca
                    resuelve el label cuando el valor se fija por código. Lookup manual.
                  */}
                  <span className={nivel == null ? "text-muted-foreground text-sm" : "text-sm"}>
                    {nivel != null && niveles.length > 0
                      ? String(niveles.find((l) => Number(l.id) === nivel)?.nombre ?? nivel)
                      : "Selecciona un nivel…"}
                  </span>
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
            {(esPregrado || nivel == null) && (
              <div className="grid gap-1.5 max-w-xs">
                <Label className="text-sm font-medium">Periodo de internado</Label>
                <Select
                  value={periodoId != null ? String(periodoId) : ""}
                  onValueChange={(v) => setPeriodoPicked(v ? Number(v) : null)}
                >
                  <SelectTrigger className="w-full min-w-[160px]">
                    <span className={periodoId == null ? "text-muted-foreground text-sm" : "text-sm"}>
                      {periodoId != null && periodos.length > 0
                        ? String(
                            periodos.find((p) => Number(p.id) === periodoId)?.nombre ??
                              periodoId,
                          )
                        : lastActivoPeriodoId != null
                          ? "Cargando…"
                          : "Todos los periodos"}
                    </span>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos los periodos</SelectItem>
                    {periodos.map((p) => (
                      <SelectItem key={String(p.id)} value={String(p.id)}>
                        {String(p.nombre ?? p.id)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </>
        ) : null}
      </div>
      {universidad == null ? (
        <EmptyPick label="Selecciona una universidad para ver sus estudiantes." />
      ) : (
        <ResourceCrud
          key={`${universidad}-${nivel ?? "x"}-${periodoId ?? "x"}`}
          config={config}
          fixedValues={{
            universidad,
            ...(esPregrado && periodoId != null ? { periodo_internado: periodoId } : {}),
          }}
          initialFilters={initialFilters}
          hideHeader
          headerActions={
            canBulkUpload ? (
              <StudentsBulkUploadDialog
                scoped={scoped}
                universidadId={universidad}
                esPregrado={esPregrado}
                periodoId={esPregrado ? periodoId : null}
              />
            ) : undefined
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
      <PageHeader title={config.title} description={config.description} />
      <div className="mb-4">{gateUI}</div>
      {universidad == null ? (
        <EmptyPick label="Selecciona una universidad para ver sus tutores." />
      ) : (
        <ResourceCrud key={universidad} config={config} initialFilters={initialFilters} hideHeader />
      )}
    </div>
  );
}
