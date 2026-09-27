"use client";

import React, { Suspense, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { GraduationCap } from "lucide-react";

import { CATALOGO_ENTITY_CONFIGS } from "@/lib/catalogos/entities";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import type { RowAction, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { api, type Paginated } from "@/lib/api/client";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { PageHeader } from "@/components/data/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// ---------- Componente: cantidad de carreras asignadas a una facultad ----------

function FacultyCarrerasCount({ facultadId }: { facultadId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["university-careers", "count-by-faculty", facultadId],
    queryFn: () =>
      api
        .get<Paginated<unknown>>("/university-careers/", {
          params: { facultad: String(facultadId), activo: "true", page_size: "1" },
        })
        .then((r) => r.data.count),
    staleTime: 2 * 60_000,
  });
  if (isLoading) return <span className="text-xs text-muted-foreground">…</span>;
  return (
    <Badge variant={data ? "secondary" : "outline"} className="tabular-nums">
      {data ?? 0}
    </Badge>
  );
}

// ---------- Componente: nombre de universidad con fallback individual ----------
// El mapa pre-carga 200 universidades ordenadas por nombre. Si el ID no está en el mapa
// (universidades más allá del rango de 200), hace fetch individual cacheado por TanStack Query.

function UniversityNameCell({
  universidadId,
  map,
}: {
  universidadId: number | null | undefined;
  map: Map<number, string>;
}) {
  const cached = universidadId != null ? map.get(universidadId) : undefined;
  const { data } = useQuery({
    queryKey: ["universities", "detail", universidadId],
    queryFn: () =>
      api.get<WithId>(`/universities/${universidadId}/`).then((r) => r.data),
    enabled: universidadId != null && cached == null,
    staleTime: 5 * 60_000,
  });

  if (cached) return <>{cached}</>;
  if (data) return <>{String((data as Record<string, unknown>).nombre ?? universidadId)}</>;
  return <span className="text-muted-foreground">{universidadId ?? "—"}</span>;
}

// ---------- Página principal (requiere Suspense por useSearchParams) ----------

function FacultadesInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const user = useAuthStore((s) => s.user);
  const baseConfig = CATALOGO_ENTITY_CONFIGS["faculties"] as ResourceConfig;

  // Filtro de universidad pre-cargado desde URL (al volver de asignación de carreras)
  const urlUniversidad = searchParams.get("universidad");
  const initialFilters = useMemo<Record<string, string> | undefined>(
    () => (urlUniversidad ? { universidad: urlUniversidad } : undefined),
    [urlUniversidad],
  );

  // Pre-carga universidades para mostrar el nombre en la columna (REQ-BACK-03: no hay _detalle)
  const universitiesQuery = useQuery({
    queryKey: ["universities", "name-map-for-faculties"],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/universities/", { params: { page_size: "200" } })
        .then((r) => r.data.results),
    staleTime: 5 * 60_000,
  });

  const universityMap = useMemo(() => {
    const m = new Map<number, string>();
    for (const u of universitiesQuery.data ?? []) {
      m.set(u.id, String((u as Record<string, unknown>).nombre ?? u.id));
    }
    return m;
  }, [universitiesQuery.data]);

  // Config enriquecida con columnas de universidad y N° carreras.
  // Orden: Logo · Universidad · Nombre · Ubicación · Activo · N° Carreras
  const config = useMemo<ResourceConfig>(() => {
    const byKey = Object.fromEntries(baseConfig.columns.map((c) => [c.key, c]));
    return {
      ...baseConfig,
      columns: [
        byKey["referencia_logo"],
        {
          key: "universidad",
          header: "Universidad",
          render: (r) =>
            React.createElement(UniversityNameCell, {
              universidadId: r.universidad as number | null,
              map: universityMap,
            }),
        },
        byKey["nombre"],
        byKey["ubigeo_detalle"],
        byKey["activo"],
        {
          key: "_n_carreras",
          header: "N° Carreras",
          render: (r) =>
            React.createElement(FacultyCarrerasCount, { facultadId: r.id }),
        },
      ].filter(Boolean),
    };
  }, [baseConfig, universityMap]);

  // Acciones por fila
  const canWrite = userHasRole(user, "Administrador RENADS");
  const rowActions = useMemo<RowAction<WithId>[]>(() => {
    if (!canWrite) return [];
    return [
      {
        key: "asignar-carreras",
        label: "Asignar carreras",
        render: (row) => {
          const universidadId = (row as Record<string, unknown>).universidad as number;
          return (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                router.push(
                  `/catalogos/entidades/university-careers?universidad=${universidadId}&facultad=${row.id}`,
                )
              }
            >
              <GraduationCap className="size-4" />
              Asignar carreras
            </Button>
          );
        },
        onClick: () => {},
      },
    ];
  }, [canWrite, router]);

  return (
    <div>
      <div className="mb-4">
        <Link href="/catalogos" className="text-sm text-muted-foreground hover:text-foreground">
          ← Catálogos
        </Link>
      </div>
      {/* PageHeader separado + hideHeader en ResourceCrud → botón Nuevo queda en la barra de filtros */}
      <PageHeader title={config.title} description={config.description} />
      <ResourceCrud
        config={config}
        rowActions={rowActions.length ? rowActions : undefined}
        initialFilters={initialFilters}
        hideHeader
      />
    </div>
  );
}

export default function FacultadesPage() {
  return (
    <Suspense>
      <FacultadesInner />
    </Suspense>
  );
}
