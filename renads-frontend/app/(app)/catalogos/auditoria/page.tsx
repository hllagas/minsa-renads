"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";

import {
  useAuditLogsList,
  type AuditLog,
  type AuditLogFilters,
} from "@/lib/api/audit-logs";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { PageHeader } from "@/components/data/page-header";
import { DataTable } from "@/components/ui/data-table";
import { DataTablePagination } from "@/components/data/data-table-pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DatePicker } from "@/components/form/date-picker";

const EMPTY: AuditLogFilters = {};

/** Quita claves vacías para no enviar params en blanco al backend. */
function clean(filters: AuditLogFilters): Record<string, string> {
  return Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v != null && v !== ""),
  ) as Record<string, string>;
}

/** Bitácora de auditoría — solo lectura, acceso `Administrador RENADS` / `Auditor`. */
export default function AuditoriaPage() {
  const user = useAuthStore((s) => s.user);
  const canAudit = userHasRole(user, "Administrador RENADS", "Auditor");

  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<AuditLogFilters>(EMPTY);

  const list = useAuditLogsList({
    page,
    // El backend ordena por `creado_en` desc por defecto.
    filters: clean(filters),
  });

  function setF(name: keyof AuditLogFilters, value: string) {
    setFilters((prev) => ({ ...prev, [name]: value }));
    setPage(1);
  }

  const columns = useMemo<ColumnDef<AuditLog>[]>(
    () => [
      {
        accessorKey: "creado_en",
        header: "Fecha",
        cell: ({ row }) => row.original.creado_en?.replace("T", " ").slice(0, 16) ?? "—",
      },
      { accessorKey: "usuario_nombre", header: "Usuario", cell: ({ row }) => row.original.usuario_nombre || "—" },
      { accessorKey: "accion", header: "Acción" },
      {
        id: "entidad",
        header: "Entidad",
        cell: ({ row }) =>
          row.original.tipo_contenido_label
            ? `${row.original.tipo_contenido_label} #${row.original.id_objeto ?? "—"}`
            : "—",
      },
      { accessorKey: "nombre_campo", header: "Campo", cell: ({ row }) => row.original.nombre_campo || "—" },
      {
        id: "cambio",
        header: "Cambio",
        cell: ({ row }) =>
          `${row.original.valor_anterior ?? "—"} → ${row.original.valor_nuevo ?? "—"}`,
      },
      { accessorKey: "direccion_ip", header: "IP", cell: ({ row }) => row.original.direccion_ip || "—" },
    ],
    [],
  );

  if (!canAudit) {
    return (
      <div>
        <PageHeader title="Bitácora de auditoría" />
        <p className="text-sm text-muted-foreground">
          No tienes permisos para consultar la bitácora.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Link href="/catalogos" className="text-sm text-muted-foreground hover:text-foreground">
          ← Catálogos
        </Link>
      </div>

      <PageHeader
        title="Bitácora de auditoría"
        description="Registro de acciones del sistema (solo lectura)."
      />

      {/* Filtros del contrato (R3): exactos + accion_contiene + rango de fechas */}
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Field label="Usuario (id)">
          <Input value={filters.usuario ?? ""} onChange={(e) => setF("usuario", e.target.value)} className="h-8 w-32" placeholder="id" />
        </Field>
        <Field label="Acción contiene">
          <Input value={filters.accion_contiene ?? ""} onChange={(e) => setF("accion_contiene", e.target.value)} className="h-8 w-40" placeholder="CREAR…" />
        </Field>
        <Field label="Entidad (id)">
          <Input value={filters.tipo_contenido ?? ""} onChange={(e) => setF("tipo_contenido", e.target.value)} className="h-8 w-32" placeholder="ContentType id" />
        </Field>
        <Field label="Objeto (id)">
          <Input value={filters.id_objeto ?? ""} onChange={(e) => setF("id_objeto", e.target.value)} className="h-8 w-28" placeholder="id" />
        </Field>
        <Field label="Desde">
          <DatePicker
            value={filters.creado_en_desde}
            onChange={(iso) => setF("creado_en_desde", iso)}
            className="h-8 w-40 justify-start gap-2 font-normal"
            placeholder="Desde"
          />
        </Field>
        <Field label="Hasta">
          <DatePicker
            value={filters.creado_en_hasta}
            onChange={(iso) => setF("creado_en_hasta", iso)}
            className="h-8 w-40 justify-start gap-2 font-normal"
            placeholder="Hasta"
          />
        </Field>
        {Object.values(filters).some((v) => v) ? (
          <Button variant="ghost" size="sm" className="h-8" onClick={() => { setFilters(EMPTY); setPage(1); }}>
            Limpiar filtros
          </Button>
        ) : null}
      </div>

      {list.isError ? (
        <div className="flex flex-col items-start gap-3 rounded-md border border-destructive/30 p-4">
          <p className="text-sm text-destructive">No se pudo cargar la bitácora.</p>
          <Button variant="outline" size="sm" onClick={() => list.refetch()} disabled={list.isFetching}>
            {list.isFetching ? "Reintentando…" : "Reintentar"}
          </Button>
        </div>
      ) : (
        <>
          <DataTable
            columns={columns as ColumnDef<AuditLog, unknown>[]}
            data={list.data?.results ?? []}
            isLoading={list.isLoading}
            emptyMessage="Sin registros."
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
