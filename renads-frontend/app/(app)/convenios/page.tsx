"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import { conventionHooks, type ConventionRead } from "@/lib/convenios/hooks";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { PageHeader } from "@/components/data/page-header";
import { DataTable } from "@/components/ui/data-table";
import { DataTablePagination } from "@/components/data/data-table-pagination";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function ConveniosPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [tipo, setTipo] = useState<number | null>(null);
  const [estado, setEstado] = useState<number | null>(null);

  // La búsqueda se aplica con retraso para no pedir al backend en cada tecla.
  const debouncedSearch = useDebouncedValue(search, 300);

  const list = conventionHooks.useList({
    page,
    search: debouncedSearch,
    ordering: "-id",
    filters: { tipo_convenio: tipo, estado_actual: estado },
  });

  const columns = useMemo<ColumnDef<ConventionRead>[]>(
    () => [
      { accessorKey: "codigo", header: "Código", cell: ({ row }) => row.original.codigo || "—" },
      { accessorKey: "titulo", header: "Título" },
      { accessorKey: "tipo_convenio", header: "Tipo" },
      {
        accessorKey: "universidad_nombre",
        header: "Universidad",
        cell: ({ row }) => row.original.universidad_nombre || "—",
      },
      {
        accessorKey: "organo_regional_nombre",
        header: "Órgano regional",
        cell: ({ row }) => row.original.organo_regional_nombre || "—",
      },
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
              render={<Link href={`/convenios/${row.original.id}`}>Ver</Link>}
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
        title="Convenios"
        description="Convenios Marco y Específicos."
        actions={
          <Button render={<Link href="/convenios/nuevo">Nuevo convenio</Link>} />
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Buscar por título o código…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="w-full sm:max-w-xs"
        />
        <div className="w-full sm:w-56">
          <EntityCombobox
            endpoint="convention-types"
            value={tipo}
            onChange={(v) => {
              setPage(1);
              setTipo(v);
            }}
            placeholder="Todos los tipos"
          />
        </div>
        <div className="w-full sm:w-56">
          <EntityCombobox
            endpoint="convention-statuses"
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
            columns={columns as ColumnDef<ConventionRead, unknown>[]}
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
