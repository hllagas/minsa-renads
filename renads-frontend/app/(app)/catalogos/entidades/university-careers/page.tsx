"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Loader2,
  Search,
  GraduationCap,
  BookOpen,
  Lock,
  Save,
  CheckSquare,
  Square,
} from "lucide-react";

import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { extractApiError } from "@/lib/api/errors";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ---------- Types ----------

interface Career extends WithId {
  nombre: string;
  nivel_academico: number | null;
  activo: boolean;
}

interface AcademicLevel extends WithId {
  nombre: string;
}

interface Faculty extends WithId {
  nombre: string;
  universidad: number;
}

interface UCLink extends WithId {
  universidad: number;
  carrera_profesional: number;
  facultad: number | null;
  activo: boolean;
}

// ---------- Data helpers ----------

async function fetchAllPages<T extends WithId>(
  endpoint: string,
  params: Record<string, string> = {},
): Promise<T[]> {
  let page = 1;
  const acc: T[] = [];
  for (;;) {
    const { data } = await api.get<Paginated<T>>(`/${endpoint}/`, {
      params: { ...params, page: String(page) },
    });
    acc.push(...data.results);
    if (!data.next) break;
    page++;
  }
  return acc;
}

// ---------- Career row state ----------

type CareerState =
  | { kind: "assigned" }           // assigned to THIS faculty
  | { kind: "free" }               // not assigned to any faculty in this university
  | { kind: "blocked"; byFaculty: string }; // assigned to another faculty

// ---------- Page ----------

export default function UniversityCareersPage() {
  const [universidadId, setUniversidadId] = useState<number | null>(null);
  const [facultadId, setFacultadId] = useState<number | null>(null);
  const [nivelId, setNivelId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  // Local selection state (derived from server + user changes)
  const [localSelected, setLocalSelected] = useState<Set<number>>(new Set());
  const [isDirty, setIsDirty] = useState(false);
  const queryClient = useQueryClient();

  // -- Catalogs --
  const careersQuery = useQuery({
    queryKey: ["professional-careers", "matrix-all"],
    queryFn: () =>
      fetchAllPages<Career>("professional-careers", { ordering: "nombre", activo: "true" }),
    staleTime: 5 * 60_000,
  });

  const levelsQuery = useQuery({
    queryKey: ["academic-levels", "matrix-all"],
    queryFn: () => fetchAllPages<AcademicLevel>("academic-levels"),
    staleTime: 10 * 60_000,
  });

  // Default nivel to "Pregrado"
  useEffect(() => {
    if (!levelsQuery.data || nivelId !== null) return;
    const pregrado = levelsQuery.data.find((l) =>
      l.nombre.toLowerCase().includes("pregrado"),
    );
    if (pregrado) setNivelId(pregrado.id);
  }, [levelsQuery.data, nivelId]);

  // -- All university-careers for this university (to detect conflicts) --
  const linksQuery = useQuery({
    queryKey: ["university-careers", "by-universidad", universidadId],
    queryFn: () =>
      fetchAllPages<UCLink>("university-careers", {
        universidad: String(universidadId!),
        activo: "true",
      }),
    enabled: universidadId != null,
    staleTime: 0,
  });

  // -- Faculties for this university --
  const facultiesQuery = useQuery({
    queryKey: ["faculties", "by-universidad", universidadId],
    queryFn: () =>
      fetchAllPages<Faculty>("faculties", {
        universidad: String(universidadId!),
      }),
    enabled: universidadId != null,
    staleTime: 5 * 60_000,
  });

  const facultyMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const f of facultiesQuery.data ?? []) m.set(f.id, f.nombre);
    return m;
  }, [facultiesQuery.data]);

  // Compute career state map once we have facultad selected
  const careerStateMap = useMemo((): Map<number, CareerState> => {
    const m = new Map<number, CareerState>();
    if (!facultadId || !linksQuery.data) return m;
    for (const link of linksQuery.data) {
      if (link.facultad === facultadId) {
        m.set(link.carrera_profesional, { kind: "assigned" });
      } else if (link.facultad != null) {
        const byFaculty = facultyMap.get(link.facultad) ?? `Facultad #${link.facultad}`;
        m.set(link.carrera_profesional, { kind: "blocked", byFaculty });
      }
    }
    return m;
  }, [linksQuery.data, facultadId, facultyMap]);

  // Server-assigned ids for this faculty (baseline)
  const serverAssignedIds = useMemo(
    () =>
      new Set(
        [...careerStateMap.entries()]
          .filter(([, s]) => s.kind === "assigned")
          .map(([id]) => id),
      ),
    [careerStateMap],
  );

  // Sync localSelected when facultad changes or data loads
  useEffect(() => {
    setLocalSelected(new Set(serverAssignedIds));
    setIsDirty(false);
  }, [serverAssignedIds]);

  const handleToggle = useCallback(
    (careerId: number, checked: boolean) => {
      setLocalSelected((prev) => {
        const next = new Set(prev);
        checked ? next.add(careerId) : next.delete(careerId);
        return next;
      });
      setIsDirty(true);
    },
    [],
  );

  // Bulk save via POST /faculties/{id}/careers/
  const saveMutation = useMutation({
    mutationFn: async () => {
      await api.post(`/faculties/${facultadId}/careers/`, {
        carreras: [...localSelected],
      });
    },
    onSuccess() {
      toast.success("Carreras guardadas correctamente");
      setIsDirty(false);
      queryClient.invalidateQueries({
        queryKey: ["university-careers", "by-universidad", universidadId],
      });
    },
    onError(err) {
      toast.error(extractApiError(err));
    },
  });

  // -- Filters --
  const careers = careersQuery.data ?? [];
  const levels = levelsQuery.data ?? [];

  const filteredCareers = useMemo(() => {
    let list = nivelId !== null
      ? careers.filter((c) => c.nivel_academico === nivelId)
      : careers;
    const q = search.trim().toLowerCase();
    if (q) list = list.filter((c) => String(c.nombre).toLowerCase().includes(q));
    return list;
  }, [careers, nivelId, search]);

  const assignedCount = useMemo(
    () => filteredCareers.filter((c) => localSelected.has(c.id)).length,
    [filteredCareers, localSelected],
  );

  const selectableInFilter = useMemo(
    () => filteredCareers.filter((c) => {
      const state = careerStateMap.get(c.id);
      return !state || state.kind !== "blocked";
    }),
    [filteredCareers, careerStateMap],
  );

  const allSelectableChecked =
    selectableInFilter.length > 0 &&
    selectableInFilter.every((c) => localSelected.has(c.id));

  const handleSelectAll = () => {
    if (allSelectableChecked) {
      setLocalSelected((prev) => {
        const next = new Set(prev);
        selectableInFilter.forEach((c) => next.delete(c.id));
        return next;
      });
    } else {
      setLocalSelected((prev) => {
        const next = new Set(prev);
        selectableInFilter.forEach((c) => next.add(c.id));
        return next;
      });
    }
    setIsDirty(true);
  };

  const isLoadingData =
    careersQuery.isLoading ||
    (universidadId != null && (linksQuery.isLoading || facultiesQuery.isLoading));

  const step2Ready = universidadId != null;
  const step3Ready = step2Ready && facultadId != null;

  return (
    <TooltipProvider>
      <div className="grid gap-6 max-w-3xl">
        {/* Back */}
        <Link
          href="/catalogos"
          className="text-sm text-muted-foreground hover:text-foreground w-fit"
        >
          ← Catálogos
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-semibold">
              Carreras Profesionales por Facultad y Universidad
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Selecciona universidad y facultad para gestionar las carreras que imparte.
            </p>
          </div>
          {step3Ready && (
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={!isDirty || saveMutation.isPending}
              size="sm"
              className="shrink-0"
            >
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Guardar cambios
            </Button>
          )}
        </div>

        {/* Step 1 — Universidad */}
        <SelectorStep
          number={1}
          label="Universidad"
          active
        >
          <EntityCombobox
            endpoint="universities"
            value={universidadId}
            onChange={(id) => {
              if (isDirty && !confirm("Tienes cambios sin guardar. ¿Cambiar de universidad?")) return;
              setUniversidadId(id);
              setFacultadId(null);
              setIsDirty(false);
            }}
            placeholder="Buscar universidad…"
            toLabel={(r) => String(r.nombre ?? r.siglas ?? r.id)}
          />
        </SelectorStep>

        {/* Step 2 — Facultad */}
        <SelectorStep
          number={2}
          label="Facultad"
          active={step2Ready}
          hint={!step2Ready ? "Primero selecciona una universidad" : undefined}
        >
          {step2Ready && (
            <EntityCombobox
              endpoint="faculties"
              params={{ universidad: String(universidadId) }}
              value={facultadId}
              onChange={(id) => {
                if (isDirty && !confirm("Tienes cambios sin guardar. ¿Cambiar de facultad?")) return;
                setFacultadId(id);
                setIsDirty(false);
              }}
              placeholder="Buscar facultad…"
              toLabel={(r) => String(r.nombre ?? r.id)}
            />
          )}
        </SelectorStep>

        {/* Step 3 — Checklist */}
        {!step3Ready ? (
          <EmptyState step={!step2Ready ? 1 : 2} />
        ) : (
          <div className="grid gap-4">
            {/* Legend */}
            <div className="flex gap-4 text-xs text-muted-foreground flex-wrap">
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-3 w-3 rounded-sm border-2 border-primary bg-primary/20" />
                Asignada a esta facultad
              </span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-3 w-3 rounded-sm border-2 border-input" />
                Disponible para asignar
              </span>
              <span className="flex items-center gap-1.5">
                <Lock className="h-3 w-3 text-muted-foreground/50" />
                Asignada a otra facultad
              </span>
            </div>

            {/* Toolbar */}
            <div className="flex items-center gap-3 flex-wrap">
              {levels.length > 0 && (
                <Select
                  value={nivelId !== null ? String(nivelId) : ""}
                  onValueChange={(v) => setNivelId(v === "" ? null : Number(v))}
                >
                  <SelectTrigger className="w-44 shrink-0">
                    <span className="truncate text-sm">
                      {nivelId !== null
                        ? (levels.find((l) => l.id === nivelId)?.nombre ?? "Nivel")
                        : "Todos los niveles"}
                    </span>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Todos los niveles</SelectItem>
                    {levels.map((l) => (
                      <SelectItem key={l.id} value={String(l.id)}>
                        {l.nombre}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <div className="relative flex-1 min-w-[160px]">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Filtrar carreras…"
                  className="pl-8"
                />
              </div>
              {linksQuery.isSuccess && (
                <Badge variant="secondary" className="shrink-0 tabular-nums">
                  {assignedCount} de {filteredCareers.length} asignadas
                </Badge>
              )}
            </div>

            {/* Table */}
            {isLoadingData ? (
              <TableSkeleton />
            ) : (
              <div className="rounded-lg border overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left font-medium text-muted-foreground px-4 py-3 w-10">
                        {/* Select-all toggle */}
                        <Tooltip>
                          <TooltipTrigger >
                            <button
                              type="button"
                              onClick={handleSelectAll}
                              className="flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
                              aria-label={allSelectableChecked ? "Deseleccionar todas" : "Seleccionar todas las disponibles"}
                            >
                              {allSelectableChecked ? (
                                <CheckSquare className="h-4 w-4" />
                              ) : (
                                <Square className="h-4 w-4" />
                              )}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent side="right">
                            {allSelectableChecked ? "Deseleccionar todas" : "Seleccionar todas las disponibles"}
                          </TooltipContent>
                        </Tooltip>
                      </th>
                      <th className="text-left font-medium text-muted-foreground px-4 py-3">
                        Carrera profesional
                      </th>
                      <th className="text-center font-medium text-muted-foreground px-4 py-3 w-10">
                        {/* empty — state icon column */}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCareers.length === 0 ? (
                      <tr>
                        <td
                          colSpan={3}
                          className="text-center text-muted-foreground py-10"
                        >
                          {search
                            ? "No hay carreras que coincidan con la búsqueda."
                            : nivelId !== null
                              ? "No hay carreras para este nivel académico."
                              : "No hay carreras disponibles."}
                        </td>
                      </tr>
                    ) : (
                      filteredCareers.map((career) => {
                        const state = careerStateMap.get(career.id);
                        const isBlocked = state?.kind === "blocked";
                        const isChecked = localSelected.has(career.id);

                        return (
                          <tr
                            key={career.id}
                            className={[
                              "border-b last:border-0 transition-colors",
                              isBlocked
                                ? "opacity-50 cursor-not-allowed"
                                : isChecked
                                  ? "bg-primary/5 hover:bg-primary/10"
                                  : "hover:bg-muted/30",
                            ]
                              .filter(Boolean)
                              .join(" ")}
                          >
                            {/* Checkbox */}
                            <td className="px-4 py-3">
                              {isBlocked ? (
                                <Tooltip>
                                  <TooltipTrigger >
                                    <span className="flex items-center justify-center cursor-not-allowed">
                                      <Lock className="h-4 w-4 text-muted-foreground/50" />
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    Asignada a:{" "}
                                    <strong>
                                      {(state as { kind: "blocked"; byFaculty: string }).byFaculty}
                                    </strong>
                                  </TooltipContent>
                                </Tooltip>
                              ) : (
                                <Checkbox
                                  checked={isChecked}
                                  onCheckedChange={(checked) =>
                                    handleToggle(career.id, !!checked)
                                  }
                                  aria-label={`${isChecked ? "Quitar" : "Asignar"} ${career.nombre}`}
                                  className="cursor-pointer"
                                />
                              )}
                            </td>

                            {/* Name */}
                            <td
                              className={[
                                "px-4 py-3 leading-snug",
                                isBlocked ? "text-muted-foreground" : "font-medium",
                              ].join(" ")}
                            >
                              {String(career.nombre)}
                              {isBlocked && (
                                <span className="block text-xs text-muted-foreground/70 mt-0.5">
                                  En uso: {(state as { kind: "blocked"; byFaculty: string }).byFaculty}
                                </span>
                              )}
                            </td>

                            {/* State badge */}
                            <td className="px-4 py-3 text-center">
                              {isChecked && !isBlocked && (
                                <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                                  Asignada
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* Dirty indicator */}
            {isDirty && (
              <p className="text-xs text-amber-600 flex items-center gap-1.5">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                Tienes cambios sin guardar. Pulsa «Guardar cambios» para confirmar.
              </p>
            )}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}

// ---------- Sub-components ----------

function SelectorStep({
  number,
  label,
  active,
  hint,
  children,
}: {
  number: number;
  label: string;
  active?: boolean;
  hint?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className={["grid gap-1.5 max-w-md transition-opacity", !active ? "opacity-40 pointer-events-none" : ""].join(" ")}>
      <label className="text-sm font-medium flex items-center gap-2">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">
          {number}
        </span>
        {label}
      </label>
      {hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : (
        children
      )}
    </div>
  );
}

function EmptyState({ step }: { step: 1 | 2 }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 gap-3 text-center">
      {step === 1 ? (
        <GraduationCap className="h-10 w-10 text-muted-foreground/40" />
      ) : (
        <BookOpen className="h-10 w-10 text-muted-foreground/40" />
      )}
      <p className="text-sm font-medium text-muted-foreground">
        {step === 1
          ? "Selecciona una universidad para continuar"
          : "Selecciona una facultad para ver sus carreras"}
      </p>
      <p className="text-xs text-muted-foreground/60 max-w-xs">
        {step === 1
          ? "Las carreras se gestionan por facultad dentro de cada universidad."
          : "Verás las carreras asignadas a esta facultad y las disponibles para agregar."}
      </p>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="bg-muted/50 px-4 py-3 border-b flex gap-4">
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-40" />
      </div>
      {Array.from({ length: 7 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3.5 border-b last:border-0">
          <Skeleton className="h-4 w-4 rounded" />
          <Skeleton className="h-4 flex-1" />
        </div>
      ))}
    </div>
  );
}
