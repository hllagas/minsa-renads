"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";

import { internshipHooks, type InternshipRead } from "@/lib/internados/hooks";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { useUniversityGate } from "@/components/internados/university-gate";
import { PageHeader } from "@/components/data/page-header";
import { DataTable } from "@/components/ui/data-table";
import { DataTablePagination } from "@/components/data/data-table-pagination";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { AnnexChecklistAction } from "@/components/almacenamiento/annex-checklist-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";

/**
 * Listado de internos: primero se elige la **universidad** (acotada al alcance), luego un
 * **convenio Específico vigente** de esa universidad (con entidad prestadora); recién entonces se
 * listan/registran los internos de ese convenio.
 */
export default function InternosPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [convenio, setConvenio] = useState<number | null>(null);
  const [estado, setEstado] = useState<number | null>(null);
  const user = useAuthStore((s) => s.user);
  const canManageAnnexes = userHasRole(user, "Universidad", "Administrador RENADS", "Interno");

  const { universidad, gateUI } = useUniversityGate();

  // Ids de «Específico» (tipo) y «Vigente» (estado) resueltos por nombre/código en runtime.
  const tiposQuery = useQuery({
    queryKey: ["convention-types", "all"],
    queryFn: () => api.get<Paginated<WithId>>("/convention-types/").then((r) => r.data.results),
    staleTime: 30 * 60_000,
  });
  const estadosQuery = useQuery({
    queryKey: ["convention-statuses", "all"],
    queryFn: () => api.get<Paginated<WithId>>("/convention-statuses/").then((r) => r.data.results),
    staleTime: 30 * 60_000,
  });
  const match = (rows: WithId[] | undefined, needle: string) =>
    rows?.find((r) =>
      `${r.codigo ?? ""} ${r.nombre ?? ""}`.toLowerCase().includes(needle),
    )?.id ?? undefined;
  const especificoId = match(tiposQuery.data, "espec");
  const vigenteId = match(estadosQuery.data, "vigente");

  // Params del combo de convenios: específicos vigentes de la universidad elegida.
  const convenioParams = useMemo<Record<string, string> | undefined>(() => {
    if (universidad == null) return undefined;
    const p: Record<string, string> = { universidad: String(universidad) };
    if (especificoId != null) p.tipo_convenio = String(especificoId);
    if (vigenteId != null) p.estado_actual = String(vigenteId);
    return p;
  }, [universidad, especificoId, vigenteId]);

  const debouncedSearch = useDebouncedValue(search, 300);
  const list = internshipHooks.useList({
    page,
    search: debouncedSearch,
    ordering: "-id",
    filters: { convenio, estado_actual: estado },
  });

  const columns = useMemo<ColumnDef<InternshipRead>[]>(
    () => [
      { accessorKey: "estudiante", header: "Estudiante" },
      { accessorKey: "convenio", header: "Convenio" },
      { accessorKey: "ipress", header: "Sede" },
      { accessorKey: "tutor", header: "Tutor" },
      { accessorKey: "estado_actual", header: "Estado" },
      {
        accessorKey: "fecha_inicio",
        header: "Inicio",
        cell: ({ row }) => row.original.fecha_inicio || "—",
      },
      {
        id: "acciones",
        header: "",
        cell: ({ row }) => (
          <div className="flex justify-end gap-2">
            {canManageAnnexes ? (
              <AnnexChecklistAction entidad="interns" row={row.original} />
            ) : null}
            <Button
              variant="outline"
              size="sm"
              render={<Link href={`/internados/${row.original.id}`}>Ver</Link>}
            />
          </div>
        ),
      },
    ],
    [canManageAnnexes],
  );

  return (
    <div>
      <div className="mb-4">
        <Link href="/internados" className="text-sm text-muted-foreground hover:text-foreground">
          ← Internados
        </Link>
      </div>
      <PageHeader
        title="Internos"
        description="Internados, rotaciones y autorizaciones."
        actions={
          convenio != null ? (
            <Button render={<Link href="/internados/nuevo">Nuevo interno</Link>} />
          ) : undefined
        }
      />

      {/* Paso 1 — universidad · Paso 2 — convenio Específico vigente */}
      <div className="mb-4 flex flex-wrap items-end gap-4">
        {gateUI}
        <div className="grid gap-1.5">
          <Label className="flex items-center gap-2 text-sm font-medium">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">
              2
            </span>
            Convenio Específico vigente
          </Label>
          <div className="w-72">
            <EntityCombobox
              key={universidad ?? 0}
              endpoint="conventions"
              params={convenioParams}
              toLabel={(r) => String(r.titulo ?? r.nomenclatura ?? r.id)}
              value={convenio}
              onChange={(v) => {
                setPage(1);
                setConvenio(v);
              }}
              disabled={universidad == null}
              placeholder={universidad == null ? "Elige universidad primero…" : "Buscar convenio…"}
            />
          </div>
        </div>
      </div>

      {universidad == null ? (
        <EmptyState label="Selecciona una universidad para continuar." />
      ) : convenio == null ? (
        <EmptyState label="Selecciona un convenio Específico vigente para ver y registrar sus internos." />
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Input
              placeholder="Buscar por estudiante…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full sm:max-w-xs"
            />
            <div className="w-full sm:w-56">
              <EntityCombobox
                endpoint="internship-statuses"
                value={estado}
                onChange={(v) => {
                  setPage(1);
                  setEstado(v);
                }}
                placeholder="Todos los estados"
              />
            </div>
          </div>

          {list.isError ? (
            <div className="flex flex-col items-start gap-3 rounded-md border border-destructive/30 p-4">
              <p className="text-sm text-destructive">No se pudo cargar el listado.</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => list.refetch()}
                disabled={list.isFetching}
              >
                {list.isFetching ? "Reintentando…" : "Reintentar"}
              </Button>
            </div>
          ) : (
            <>
              <DataTable
                columns={columns as ColumnDef<InternshipRead, unknown>[]}
                data={list.data?.results ?? []}
                isLoading={list.isLoading}
              />
              <DataTablePagination
                page={page}
                count={list.data?.count ?? 0}
                onPageChange={setPage}
                isFetching={list.isFetching}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
    </div>
  );
}
