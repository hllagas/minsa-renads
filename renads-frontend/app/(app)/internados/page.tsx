"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { internshipHooks, type InternshipRead } from "@/lib/internados/hooks";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { PageHeader } from "@/components/data/page-header";
import { DataTable } from "@/components/ui/data-table";
import { DataTablePagination } from "@/components/data/data-table-pagination";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function InternadosPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [convenio, setConvenio] = useState<number | null>(null);
  const [estado, setEstado] = useState<number | null>(null);

  const debouncedSearch = useDebouncedValue(search, 300);

  const list = internshipHooks.useList({
    page,
    search: debouncedSearch,
    ordering: "-id",
    filters: { convenio, estado_actual: estado },
  });

  const columns = useMemo<ColumnDef<InternshipRead>[]>(
    () => [
      { accessorKey: "interno", header: "Interno" },
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
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              render={<Link href={`/internados/${row.original.id}`}>Ver</Link>}
            />
          </div>
        ),
      },
    ],
    [],
  );

  return (
    <div>
      <PageHeader
        title="Internados"
        description="Internados, rotaciones y autorizaciones."
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline"
              render={<Link href="/internados/personas">Personas</Link>}
            />
            <Button render={<Link href="/internados/nuevo">Nuevo internado</Link>} />
          </div>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Buscar por interno…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="w-full sm:max-w-xs"
        />
        <div className="w-full sm:w-56">
          <EntityCombobox
            endpoint="conventions"
            toLabel={(r) => String(r.titulo ?? r.codigo ?? r.id)}
            value={convenio}
            onChange={(v) => {
              setPage(1);
              setConvenio(v);
            }}
            placeholder="Todos los convenios"
          />
        </div>
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
          <p className="text-sm text-destructive">
            No se pudo cargar el listado.
          </p>
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
    </div>
  );
}
