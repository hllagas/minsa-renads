"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { buildStudentsConfig, buildTutorsConfig, buildCoordinatorsConfig } from "@/lib/internados/persons";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { TutorCreateWizard } from "@/components/internados/tutor-create-wizard";
import { TutorConvenioDialog } from "@/components/internados/tutor-convenio-dialog";
import { CoordinatorSedesDialog } from "@/components/internados/coordinator-sedes-dialog";
import { useUniversityScope } from "@/lib/auth/scope";
import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import type { RowAction } from "@/lib/crud/types";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { StudentsBulkUploadDialog } from "@/components/internados/students-bulk-upload-dialog";
import { useUniversityGate } from "@/components/internados/university-gate";
import { UniversityLogoDisplay } from "@/components/internados/university-logo-display";
import { extractApiError } from "@/lib/api/errors";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { PageHeader } from "@/components/data/page-header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
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
  if (entidad === "coordinators") return <CoordinatorsView />;

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
    <div className="mb-1">
      <Link href="/internados" className="text-sm text-muted-foreground hover:text-foreground">
        ← Internado
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
      <PageHeader
        title="Estudiantes"
        description="Estudiantes en proceso de internado."
        actions={universidad != null ? <UniversityLogoDisplay id={universidad} /> : undefined}
      />
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

type UnivInfo = { id: number; nombre: string; siglas: string };

/** Muestra las universidades asignadas al tutor en modo solo lectura dentro del form de edición. */
function TutorUniversidades({
  row,
  universidad,
}: {
  row: WithId;
  universidad: number | null;
}) {
  const univsDet = (row.universidades_detalle as UnivInfo[] | undefined) ?? [];
  if (univsDet.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin universidades asignadas.</p>;
  }
  return (
    <div className="grid gap-1.5">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Universidades asignadas
      </p>
      <div className="flex flex-wrap gap-1.5">
        {univsDet.map((u) => (
          <span
            key={u.id}
            className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-sm ${
              u.id === universidad
                ? "border-primary/50 bg-primary/5 font-medium text-primary"
                : "text-muted-foreground"
            }`}
          >
            {u.siglas || u.nombre}
            {u.id === universidad && (
              <span className="text-xs opacity-70">• universidad actual</span>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Vista de coordinadores: elegir universidad (acotada al alcance) → listar los coordinadores
 * con sedes en esa universidad (filtro `sedes__universidad`).
 */
function CoordinatorsView() {
  const user = useAuthStore((s) => s.user);
  const canWrite = userHasRole(user, "Universidad", "Administrador RENADS");
  const { universidad, gateUI } = useUniversityGate();
  const queryClient = useQueryClient();
  const config = useMemo(() => buildCoordinatorsConfig(), []);
  const initialFilters = useMemo<Record<string, string> | undefined>(
    () =>
      universidad != null ? { universidad: String(universidad) } : undefined,
    [universidad],
  );

  // Estado para el dialog de sedes
  const [sedesCoordinador, setSedesCoordinador] = useState<{
    id: number;
    nombre: string;
  } | null>(null);

  // Estado para el dialog de asignar tutor
  const [asignarTutorTarget, setAsignarTutorTarget] = useState<{
    id: number;
    nombre: string;
    tutorActual: number | null;
  } | null>(null);
  const [tutorPick, setTutorPick] = useState<number | null>(null);

  const asignarMutation = useMutation({
    mutationFn: ({ coordId, tutorId }: { coordId: number; tutorId: number | null }) =>
      api.patch(`/coordinators/${coordId}/`, { tutor: tutorId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coordinators"] });
      toast.success(tutorPick != null ? "Tutor asignado correctamente." : "Tutor desvinculado.");
      setAsignarTutorTarget(null);
      setTutorPick(null);
    },
    onError: (e) => toast.error(extractApiError(e)),
  });

  // Helper inline para apellidos+nombres
  const apellidosNombresInline = (row: WithId): string =>
    [row.apellido_paterno, row.apellido_materno, row.nombres]
      .map((x) => String(x ?? "").trim())
      .filter(Boolean)
      .join(" ");

  const tutorParams = useMemo<Record<string, string> | undefined>(
    () => (universidad != null ? { universidades: String(universidad) } : undefined),
    [universidad],
  );

  const rowActions: RowAction<WithId>[] = useMemo(
    () => [
      {
        key: "sedes",
        label: "Sedes",
        variant: "outline" as const,
        onClick: (row: WithId) =>
          setSedesCoordinador({
            id: Number(row.id),
            nombre: apellidosNombresInline(row),
          }),
      },
      ...(canWrite
        ? [
            {
              key: "asignar-tutor",
              label: "Asignar tutor",
              variant: "outline" as const,
              onClick: (row: WithId) => {
                const tutorId =
                  row.tutor != null && row.tutor !== "" ? Number(row.tutor) : null;
                setTutorPick(tutorId);
                setAsignarTutorTarget({
                  id: Number(row.id),
                  nombre: apellidosNombresInline(row),
                  tutorActual: tutorId,
                });
              },
            },
          ]
        : []),
    ],
    [canWrite, universidad],
  );

  return (
    <div>
      <BackLink />
      <PageHeader
        title={config.title}
        description={config.description}
        actions={
          universidad != null ? <UniversityLogoDisplay id={universidad} /> : undefined
        }
      />
      <div className="mb-4">{gateUI}</div>
      {universidad == null ? (
        <EmptyPick label="Selecciona una universidad para ver sus coordinadores." />
      ) : (
        <>
          <ResourceCrud
            key={universidad}
            config={config}
            initialFilters={initialFilters}
            fixedValues={universidad != null ? { universidad } : undefined}
            hideHeader
            rowActions={rowActions}
          />

          {/* Dialog: sedes del coordinador */}
          {sedesCoordinador != null && (
            <CoordinatorSedesDialog
              coordinatorId={sedesCoordinador.id}
              coordinatorNombre={sedesCoordinador.nombre}
              open={sedesCoordinador !== null}
              onOpenChange={(open) => {
                if (!open) setSedesCoordinador(null);
              }}
              universidad={universidad}
              canWrite={canWrite}
            />
          )}

          {/* Dialog: asignar tutor al coordinador */}
          <Dialog
            open={asignarTutorTarget !== null}
            onOpenChange={(open) => {
              if (!open) {
                setAsignarTutorTarget(null);
                setTutorPick(null);
              }
            }}
          >
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>
                  Asignar tutor — {asignarTutorTarget?.nombre}
                </DialogTitle>
              </DialogHeader>
              <div className="flex flex-col gap-4 py-2">
                <p className="text-sm text-muted-foreground">
                  Selecciona un tutor registrado en esta universidad que aún no haya
                  sido asignado a otro coordinador.
                </p>
                <div className="grid gap-1.5">
                  <Label className="text-sm font-medium">Tutor</Label>
                  <EntityCombobox<number>
                    endpoint="tutors"
                    params={tutorParams}
                    toLabel={(r) =>
                      [r.apellido_paterno, r.apellido_materno, r.nombres]
                        .map((x) => String(x ?? "").trim())
                        .filter(Boolean)
                        .join(" ")
                    }
                    value={tutorPick}
                    onChange={setTutorPick}
                    placeholder="Buscar tutor…"
                  />
                </div>
                {asignarTutorTarget?.tutorActual != null && (
                  <p className="text-xs text-muted-foreground">
                    El coordinador ya tiene un tutor vinculado. Seleccionar uno nuevo lo
                    reemplazará.
                  </p>
                )}
              </div>
              <DialogFooter className="gap-2">
                {asignarTutorTarget?.tutorActual != null && (
                  <Button
                    variant="outline"
                    disabled={asignarMutation.isPending}
                    onClick={() =>
                      asignarMutation.mutate({
                        coordId: asignarTutorTarget.id,
                        tutorId: null,
                      })
                    }
                  >
                    Desvincular tutor
                  </Button>
                )}
                <Button
                  disabled={tutorPick == null || asignarMutation.isPending}
                  onClick={() => {
                    if (asignarTutorTarget && tutorPick != null)
                      asignarMutation.mutate({
                        coordId: asignarTutorTarget.id,
                        tutorId: tutorPick,
                      });
                  }}
                >
                  {asignarMutation.isPending ? "Asignando…" : "Asignar"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </>
      )}
    </div>
  );
}

/**
 * Vista de tutores: elegir universidad (acotada al alcance) → listar los tutores de esa universidad
 * (filtro `universidades`). No usa `fixedValues` porque `universidades` es M2M (RN-24).
 */
function TutorsView() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = userHasRole(user, "Administrador RENADS");
  const canWrite = userHasRole(user, "Universidad", "Administrador RENADS");
  const { universidad, gateUI } = useUniversityGate();
  const queryClient = useQueryClient();
  const config = useMemo(() => buildTutorsConfig(isAdmin, universidad), [isAdmin, universidad]);
  const initialFilters = useMemo<Record<string, string> | undefined>(
    () => (universidad != null ? { universidades: String(universidad) } : undefined),
    [universidad],
  );
  const [wizardOpen, setWizardOpen] = useState(false);

  // Estado para el dialog de gestión de TutorConvenio
  const [conveniosTutor, setConveniosTutor] = useState<{ id: number; nombre: string } | null>(null);

  // Helper inline que replica la lógica de `apellidosNombres` de lib/internados/persons.ts
  const apellidosNombresInline = (row: WithId): string =>
    [row.apellido_paterno, row.apellido_materno, row.nombres]
      .map((x) => String(x ?? "").trim())
      .filter(Boolean)
      .join(" ");

  // Row action «Convenios asignados» — visible para todos los roles autenticados
  const rowActions: RowAction<WithId>[] = useMemo(
    () => [
      {
        key: "convenios",
        label: "Convenios asignados",
        variant: "outline" as const,
        onClick: (row: WithId) =>
          setConveniosTutor({
            id: Number(row.id),
            nombre: apellidosNombresInline(row),
          }),
      },
    ],
    [],
  );

  async function handleTutorDelete(row: WithId, close: () => void) {
    // IDs actuales de universidades del tutor. La lista puede exponerlos como
    // `universidades_detalle` (objetos) o `universidades` (ids planos u objetos).
    // Se coercionan a number para comparar sin mismatch de tipo (bug: string vs number).
    const extractIds = (v: unknown): number[] => {
      if (!Array.isArray(v)) return [];
      return v
        .map((x) =>
          x != null && typeof x === "object" && "id" in x
            ? Number((x as { id: unknown }).id)
            : Number(x),
        )
        .filter((n) => Number.isFinite(n));
    };

    const currentUnivIds =
      extractIds(row.universidades_detalle).length > 0
        ? extractIds(row.universidades_detalle)
        : extractIds(row.universidades);
    const target = Number(universidad);
    const remaining = currentUnivIds.filter((id) => id !== target);

    const refresh = () =>
      queryClient.invalidateQueries({ queryKey: ["tutors"], refetchType: "all" });

    try {
      if (remaining.length > 0) {
        // Tutor tiene otras universidades → solo quitar esta del M2M
        await api.patch(`/tutors/${row.id}/`, { universidades: remaining });
        toast.success("Tutor desvinculado de esta universidad.");
      } else {
        // Sin otras universidades → eliminar la ficha completa
        await api.delete(`/tutors/${row.id}/`);
        toast.success("Tutor eliminado.");
      }
      await refresh();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      close();
    }
  }

  return (
    <div>
      <BackLink />
      <PageHeader
        title={config.title}
        description={config.description}
        actions={universidad != null ? <UniversityLogoDisplay id={universidad} /> : undefined}
      />
      <div className="mb-4">{gateUI}</div>
      {universidad == null ? (
        <EmptyPick label="Selecciona una universidad para ver sus tutores." />
      ) : (
        <>
          <ResourceCrud
            key={universidad}
            config={config}
            initialFilters={initialFilters}
            hideHeader
            onDelete={handleTutorDelete}
            rowActions={rowActions}
            renderEditInfo={(row) => (
              <TutorUniversidades row={row} universidad={universidad} />
            )}
            headerActions={
              canWrite ? (
                <Button onClick={() => setWizardOpen(true)}>Nuevo tutor</Button>
              ) : undefined
            }
          />
          {canWrite && (
            <TutorCreateWizard
              universidad={universidad}
              open={wizardOpen}
              onOpenChange={setWizardOpen}
            />
          )}
          {conveniosTutor != null && (
            <TutorConvenioDialog
              tutorId={conveniosTutor.id}
              tutorNombre={conveniosTutor.nombre}
              open={conveniosTutor !== null}
              onOpenChange={(open) => {
                if (!open) setConveniosTutor(null);
              }}
              universidad={universidad}
              canWrite={canWrite}
            />
          )}
        </>
      )}
    </div>
  );
}
