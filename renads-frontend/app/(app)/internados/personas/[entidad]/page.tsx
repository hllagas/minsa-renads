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
import { EntityCombobox } from "@/components/form/entity-combobox";
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

  const config = PERSON_CONFIGS[entidad];
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

  return (
    <div>
      <BackLink />
      <ResourceCrud config={config} />
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

/**
 * Vista de estudiantes: primero se elige la universidad (acotada al alcance del usuario), luego se
 * lista/gestiona. La universidad elegida se fija (oculta) en el form y filtra el listado. El filtro
 * de nivel académico arranca en «Pregrado» (id resuelto en runtime).
 */
function StudentsView() {
  const user = useAuthStore((s) => s.user);
  const { ids, singleId, scoped } = useUniversityScope();
  const canBulkUpload = userHasRole(user, "Universidad", "Administrador RENADS");

  // Universidad elegida (si el usuario tiene una sola, se autofija).
  const [pickedUni, setPickedUni] = useState<number | null>(singleId);
  const universidad = singleId ?? pickedUni;

  // Nivel «Pregrado» (default del filtro + driver del toggle carrera/especialidad).
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

      {/* Paso 1 — elegir universidad (acotada al alcance) */}
      <div className="mb-4 grid gap-1.5 max-w-md">
        <Label className="flex items-center gap-2 text-sm font-medium">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">
            1
          </span>
          Universidad
        </Label>
        {singleId != null ? (
          <p className="text-sm text-muted-foreground">
            Acotado a tu universidad autorizada.
          </p>
        ) : scoped ? (
          <ScopedUniversitySelect ids={ids} value={pickedUni} onChange={setPickedUni} />
        ) : (
          <EntityCombobox
            endpoint="universities"
            value={pickedUni}
            onChange={setPickedUni}
            toLabel={(r) => String(r.nombre ?? r.siglas ?? r.id)}
            placeholder="Buscar universidad…"
          />
        )}
      </div>

      {universidad == null ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
          <p className="text-sm font-medium text-muted-foreground">
            Selecciona una universidad para ver sus estudiantes.
          </p>
        </div>
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

/** Selector de universidad acotado a los ids autorizados del usuario (alcance múltiple). */
function ScopedUniversitySelect({
  ids,
  value,
  onChange,
}: {
  ids: number[];
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const query = useQuery({
    queryKey: ["universities", "scoped", ids],
    queryFn: () =>
      api.get<Paginated<WithId>>("/universities/").then((r) => r.data.results),
    staleTime: 10 * 60_000,
  });
  const opciones = (query.data ?? []).filter((u) => ids.includes(Number(u.id)));

  return (
    <Select
      value={value != null ? String(value) : ""}
      onValueChange={(v) => onChange(v ? Number(v) : null)}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Selecciona una universidad…" />
      </SelectTrigger>
      <SelectContent>
        {opciones.map((u) => (
          <SelectItem key={u.id} value={String(u.id)}>
            {String(u.nombre ?? u.siglas ?? u.id)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
