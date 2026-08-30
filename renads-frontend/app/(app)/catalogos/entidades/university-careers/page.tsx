"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Search, GraduationCap } from "lucide-react";

import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { extractApiError } from "@/lib/api/errors";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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

interface UCLink extends WithId {
  universidad: number;
  carrera_profesional: number;
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

// ---------- Page ----------

export default function UniversityCareersPage() {
  const [universidadId, setUniversidadId] = useState<number | null>(null);
  const [nivelId, setNivelId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set());
  const queryClient = useQueryClient();

  const careersQuery = useQuery({
    queryKey: ["professional-careers", "matrix-all"],
    queryFn: () =>
      fetchAllPages<Career>("professional-careers", { ordering: "nombre" }),
    staleTime: 5 * 60_000,
  });

  const levelsQuery = useQuery({
    queryKey: ["academic-levels", "matrix-all"],
    queryFn: () => fetchAllPages<AcademicLevel>("academic-levels"),
    staleTime: 10 * 60_000,
  });

  // Default nivel to "Pregrado" once levels are loaded
  useEffect(() => {
    if (!levelsQuery.data || nivelId !== null) return;
    const pregrado = levelsQuery.data.find((l) =>
      l.nombre.toLowerCase().includes("pregrado"),
    );
    if (pregrado) setNivelId(pregrado.id);
  }, [levelsQuery.data, nivelId]);

  const linksQuery = useQuery({
    queryKey: ["university-careers", "by-universidad", universidadId],
    queryFn: () =>
      fetchAllPages<UCLink>("university-careers", {
        universidad: String(universidadId!),
      }),
    enabled: universidadId != null,
    staleTime: 0,
  });

  const activeCareerIds = useMemo(
    () =>
      new Set(
        (linksQuery.data ?? [])
          .filter((l) => l.activo)
          .map((l) => l.carrera_profesional),
      ),
    [linksQuery.data],
  );

  const linkByCareer = useMemo(() => {
    const m = new Map<number, UCLink>();
    for (const l of linksQuery.data ?? []) m.set(l.carrera_profesional, l);
    return m;
  }, [linksQuery.data]);

  const toggleMutation = useMutation({
    mutationFn: async ({
      careerId,
      enable,
    }: {
      careerId: number;
      enable: boolean;
    }) => {
      const existing = linkByCareer.get(careerId);
      if (enable) {
        if (existing) {
          await api.patch(`/university-careers/${existing.id}/`, {
            activo: true,
          });
        } else {
          await api.post("/university-careers/", {
            universidad: universidadId,
            carrera_profesional: careerId,
            activo: true,
          });
        }
      } else if (existing) {
        await api.patch(`/university-careers/${existing.id}/`, {
          activo: false,
        });
      }
    },
    onMutate({ careerId }) {
      setPendingIds((prev) => new Set([...prev, careerId]));
    },
    onSuccess() {
      queryClient.invalidateQueries({
        queryKey: ["university-careers", "by-universidad", universidadId],
      });
    },
    onError(err) {
      toast.error(extractApiError(err));
    },
    onSettled(_, __, { careerId }) {
      setPendingIds((prev) => {
        const next = new Set(prev);
        next.delete(careerId);
        return next;
      });
    },
  });

  const careers = careersQuery.data ?? [];
  const levels = levelsQuery.data ?? [];

  // Careers filtered by nivel + text search
  const filteredCareers = useMemo(() => {
    let list = nivelId !== null
      ? careers.filter((c) => c.nivel_academico === nivelId)
      : careers;
    const q = search.trim().toLowerCase();
    if (q) list = list.filter((c) => String(c.nombre).toLowerCase().includes(q));
    return list;
  }, [careers, nivelId, search]);

  // Count only within the current nivel filter
  const enabledInFilter = filteredCareers.filter((c) =>
    activeCareerIds.has(c.id),
  ).length;

  const isLoading =
    careersQuery.isLoading ||
    (universidadId != null && linksQuery.isLoading);

  return (
    <div className="grid gap-6 max-w-2xl">
      <Link
        href="/catalogos"
        className="text-sm text-muted-foreground hover:text-foreground w-fit"
      >
        ← Catálogos
      </Link>

      <div>
        <h1 className="text-xl font-semibold">Carreras por Universidad</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Selecciona una universidad y marca las carreras profesionales que dicta.
        </p>
      </div>

      {/* Universidad selector */}
      <div className="grid gap-1.5 max-w-md">
        <label className="text-sm font-medium">Universidad</label>
        <EntityCombobox
          endpoint="universities"
          value={universidadId}
          onChange={(id) => {
            setUniversidadId(id);
            setSearch("");
          }}
          placeholder="Buscar universidad…"
          toLabel={(r) => String(r.nombre ?? r.siglas ?? r.id)}
        />
      </div>

      {!universidadId ? (
        <EmptyUniversityState />
      ) : (
        <div className="grid gap-4">
          {/* Toolbar: nivel + búsqueda + contador */}
          <div className="flex items-center gap-3 flex-wrap">
            {levels.length > 0 && (
              <Select
                value={nivelId !== null ? String(nivelId) : ""}
                onValueChange={(v) =>
                  setNivelId(v === "" ? null : Number(v))
                }
              >
                <SelectTrigger className="w-48 shrink-0">
                  <span className="truncate text-sm">
                    {nivelId !== null
                      ? (levels.find((l) => l.id === nivelId)?.nombre ??
                        "Nivel académico")
                      : "Todos los niveles"}
                  </span>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos los niveles</SelectItem>
                  {levels.map((level) => (
                    <SelectItem key={level.id} value={String(level.id)}>
                      {level.nombre}
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
                {enabledInFilter} de {filteredCareers.length} habilitadas
              </Badge>
            )}
          </div>

          {/* Table */}
          {isLoading ? (
            <TableSkeleton />
          ) : (
            <div className="rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left font-medium text-muted-foreground px-4 py-3">
                      Carrera profesional
                    </th>
                    <th className="text-center font-medium text-muted-foreground px-4 py-3 w-28">
                      Habilitada
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCareers.length === 0 ? (
                    <tr>
                      <td
                        colSpan={2}
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
                      const isChecked = activeCareerIds.has(career.id);
                      const isPending = pendingIds.has(career.id);

                      return (
                        <tr
                          key={career.id}
                          className={[
                            "border-b last:border-0 transition-colors hover:bg-muted/30",
                            isChecked ? "bg-primary/5 hover:bg-primary/10" : "",
                          ]
                            .filter(Boolean)
                            .join(" ")}
                        >
                          <td className="px-4 py-3 font-medium leading-snug">
                            {String(career.nombre)}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-center">
                              {isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                              ) : (
                                <Checkbox
                                  checked={isChecked}
                                  onCheckedChange={(checked) =>
                                    toggleMutation.mutate({
                                      careerId: career.id,
                                      enable: !!checked,
                                    })
                                  }
                                  aria-label={`${isChecked ? "Deshabilitar" : "Habilitar"} ${career.nombre}`}
                                  className="cursor-pointer"
                                />
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmptyUniversityState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 gap-3 text-center">
      <GraduationCap className="h-10 w-10 text-muted-foreground/40" />
      <p className="text-sm font-medium text-muted-foreground">
        Selecciona una universidad para gestionar sus carreras
      </p>
      <p className="text-xs text-muted-foreground/60 max-w-xs">
        Podrás habilitar o deshabilitar las carreras profesionales que dicta la
        universidad seleccionada.
      </p>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="bg-muted/50 px-4 py-3 border-b flex gap-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-20 ml-auto" />
      </div>
      {Array.from({ length: 7 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-4 px-4 py-3.5 border-b last:border-0"
        >
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-4 rounded ml-auto" />
        </div>
      ))}
    </div>
  );
}
