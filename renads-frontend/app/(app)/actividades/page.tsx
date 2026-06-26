"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import {
  teachingActivityHooks,
  type TeachingActivityRead,
} from "@/lib/actividades/hooks";
import { PageHeader } from "@/components/data/page-header";
import { DataTable } from "@/components/ui/data-table";
import { DataTablePagination } from "@/components/data/data-table-pagination";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function ActividadesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [tipo, setTipo] = useState<number | null>(null);
  const [estado, setEstado] = useState<number | null>(null);

  const list = teachingActivityHooks.useList({
    page,
    search,
    ordering: "-id",
    filters: { tipo_actividad: tipo, estado_actual: estado },
  });

  const columns = useMemo<ColumnDef<TeachingActivityRead>[]>(
    () => [
      { accessorKey: "interno", header: "Interno" },
      { accessorKey: "ipress", header: "Sede" },
      { accessorKey: "tipo_actividad", header: "Tipo" },
      { accessorKey: "estado_actual", header: "Estado" },
      {
        accessorKey: "fecha_actividad",
        header: "Fecha",
        cell: ({ row }) => row.original.fecha_actividad || "—",
      },
      {
        id: "acciones",
        header: "",
        cell: ({ row }) => (
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              render={<Link href={`/actividades/${row.original.id}`}>Ver</Link>}
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
        title="Actividades"
        description="Actividades docente-asistenciales de los internos."
        actions={
          <Button render={<Link href="/actividades/nueva">Nueva actividad</Link>} />
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Buscar por descripción…"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          className="max-w-xs"
        />
        <div className="w-56">
          <EntityCombobox
            endpoint="activity-types"
            value={tipo}
            onChange={(v) => {
              setPage(1);
              setTipo(v);
            }}
            placeholder="Todos los tipos"
          />
        </div>
        <div className="w-56">
          <EntityCombobox
            endpoint="activity-statuses"
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
        <p className="text-sm text-destructive">No se pudo cargar el listado.</p>
      ) : (
        <>
          <DataTable
            columns={columns as ColumnDef<TeachingActivityRead, unknown>[]}
            data={list.data?.results ?? []}
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
