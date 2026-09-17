"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Layers, CheckSquare, ArrowRightSquare } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { PageHeader } from "@/components/data/page-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";

const NAV_CARDS = [
  {
    href: "/campos-clinicos/registros",
    title: "Determinación de campos de formación",
    description:
      "Campos de formación determinados a cada sede docente y carrera profesional (CONAPRES).",
  },
  {
    href: "/campos-clinicos/asignaciones",
    title: "Asignación de campos de formación",
    description:
      "Campos de formación asignados a cada universidad, según disponibilidad en cada sede docente (Órgano Regional).",
  },
];

function KpiCard({
  title,
  value,
  icon: Icon,
  loading,
}: {
  title: string;
  value: number;
  icon?: LucideIcon;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-20" />
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          {Icon && <Icon className="size-4" />}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{value.toLocaleString("es-PE")}</p>
      </CardContent>
    </Card>
  );
}

export default function CamposClinicosPage() {
  const [nivelId, setNivelId] = useState<number | null>(null);

  const nivelesQuery = useQuery({
    queryKey: ["academic-levels", "all"],
    queryFn: () =>
      api.get<Paginated<WithId>>("/academic-levels/").then((r) => r.data.results),
    staleTime: 30 * 60_000,
  });

  const niveles = useMemo(() => nivelesQuery.data ?? [], [nivelesQuery.data]);

  const resolvedNivelId = useMemo(() => {
    if (nivelId != null) return nivelId;
    const pregrado = niveles.find((n) =>
      `${n.nombre ?? ""} ${n.codigo ?? ""}`.toLowerCase().includes("pregrado"),
    );
    return pregrado?.id ?? null;
  }, [nivelId, niveles]);

  const registrosQuery = useQuery({
    queryKey: ["clinical-field-registrations", "kpi", resolvedNivelId],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/clinical-field-registrations/", {
          params: {
            carrera_profesional__nivel_academico: resolvedNivelId,
            page_size: 500,
          },
        })
        .then((r) => r.data),
    enabled: resolvedNivelId != null,
    staleTime: 2 * 60_000,
  });

  const asignacionesQuery = useQuery({
    queryKey: ["clinical-field-allocations", "kpi"],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/clinical-field-allocations/", {
          params: { page_size: 500 },
        })
        .then((r) => r.data),
    staleTime: 2 * 60_000,
  });

  const kpiRegistros = useMemo(() => {
    const rows = registrosQuery.data?.results ?? [];
    return {
      determinados: rows.reduce((s, r) => s + (Number(r.campos_clinicos_registrados) || 0), 0),
      asignados: rows.reduce((s, r) => s + (Number(r.campos_clinicos_asignados) || 0), 0),
      disponibles: rows.reduce((s, r) => s + (Number(r.disponibilidad) || 0), 0),
    };
  }, [registrosQuery.data]);

  const kpiAsignaciones = useMemo(() => {
    const data = asignacionesQuery.data;
    return {
      total: data?.count ?? 0,
      autorizados: (data?.results ?? []).reduce(
        (s, r) => s + (Number(r.campos_clinicos_autorizados) || 0),
        0,
      ),
    };
  }, [asignacionesQuery.data]);

  const registrosLoading = resolvedNivelId == null || registrosQuery.isLoading;
  const asignacionesLoading = asignacionesQuery.isLoading;

  return (
    <div className="grid gap-8">
      <PageHeader
        title="Campos de formación"
        description="Determinación y Registro (CONAPRES) y asignación por universidad (Órgano Regional)."
      />

      {/* Selector de nivel académico */}
      <div className="grid gap-1.5 max-w-xs">
        <Label className="text-sm font-medium">Nivel académico</Label>
        <Select
          disabled={nivelesQuery.isLoading}
          value={resolvedNivelId != null ? String(resolvedNivelId) : ""}
          onValueChange={(v) => setNivelId(Number(v))}
        >
          <SelectTrigger>
            <SelectValue placeholder="Selecciona un nivel…" />
          </SelectTrigger>
          <SelectContent>
            {niveles.map((n) => (
              <SelectItem key={n.id} value={String(n.id)}>
                {String(n.nombre ?? n.id)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* KPI — Determinación de campos */}
      <div className="grid gap-4">
        <h2 className="text-base font-semibold">Determinación de campos</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <KpiCard
            title="Total determinados"
            value={kpiRegistros.determinados}
            icon={Layers}
            loading={registrosLoading}
          />
          <KpiCard
            title="Total asignados"
            value={kpiRegistros.asignados}
            icon={CheckSquare}
            loading={registrosLoading}
          />
          <KpiCard
            title="Total disponibles"
            value={kpiRegistros.disponibles}
            icon={ArrowRightSquare}
            loading={registrosLoading}
          />
        </div>
      </div>

      {/* KPI — Asignación de campos */}
      <div className="grid gap-4">
        <h2 className="text-base font-semibold">Asignación de campos</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <KpiCard
            title="Total asignaciones"
            value={kpiAsignaciones.total}
            loading={asignacionesLoading}
          />
          <KpiCard
            title="Total cupos autorizados"
            value={kpiAsignaciones.autorizados}
            loading={asignacionesLoading}
          />
        </div>
      </div>

      {/* Tarjetas de navegación existentes */}
      <div className="grid gap-4 sm:grid-cols-2">
        {NAV_CARDS.map((c) => (
          <Link key={c.href} href={c.href}>
            <Card className="h-full transition-colors hover:bg-muted/50">
              <CardHeader>
                <CardTitle>{c.title}</CardTitle>
                <CardDescription>{c.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
