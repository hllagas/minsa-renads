"use client";

import { useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";

import type { ResourceConfig } from "@/lib/crud/types";
import { createResourceHooks } from "@/lib/crud/hooks";
import type { WithId } from "@/lib/api/query";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { extractApiError } from "@/lib/api/errors";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";

import { PageHeader } from "@/components/data/page-header";
import { DataTable } from "@/components/ui/data-table";
import { DataTablePagination } from "@/components/data/data-table-pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ResourceForm } from "@/components/crud/resource-form";

const WRITE_ROLES = ["Administrador RENADS"];

/**
 * CRUD declarativo de un recurso maestro (DRF). Lista paginada/búsqueda + alta/edición en diálogo
 * + borrado. La escritura está gateada a `Administrador RENADS` (la autoridad final es el backend).
 */
export function ResourceCrud<TRead extends WithId>({
  config,
}: {
  config: ResourceConfig<TRead>;
}) {
  const hooks = useMemo(
    () => createResourceHooks<TRead, Record<string, unknown>>(config.endpoint),
    [config.endpoint],
  );

  const user = useAuthStore((s) => s.user);
  const canWrite = userHasRole(user, ...(config.writeRoles ?? WRITE_ROLES));

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<TRead | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<TRead | null>(null);

  // La búsqueda se aplica con retraso para no pedir al backend en cada tecla.
  const debouncedSearch = useDebouncedValue(search, 300);
  useEffect(() => setPage(1), [debouncedSearch]);

  const list = hooks.useList({ page, search: debouncedSearch, ordering: "id" });
  const createM = hooks.useCreate();
  const updateM = hooks.useUpdate();
  const removeM = hooks.useRemove();

  const columns = useMemo<ColumnDef<TRead>[]>(() => {
    const base: ColumnDef<TRead>[] = config.columns.map((c) => ({
      accessorKey: c.key,
      header: c.header,
      cell: ({ row }) =>
        c.render ? c.render(row.original) : String(row.original[c.key] ?? "—"),
    }));
    if (canWrite) {
      base.push({
        id: "acciones",
        header: "",
        cell: ({ row }) => (
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setEditing(row.original);
                setDialogOpen(true);
              }}
            >
              Editar
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setDeleting(row.original)}
            >
              Eliminar
            </Button>
          </div>
        ),
      });
    }
    return base;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.columns, canWrite]);

  function onCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function confirmDelete() {
    if (!deleting) return;
    removeM.mutate(deleting.id, {
      onSuccess: () => {
        toast.success(`${config.singular} eliminada.`);
        setDeleting(null);
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  function onSubmit(payload: Record<string, unknown>) {
    const opts = {
      onSuccess: () => {
        toast.success(editing ? "Cambios guardados." : `${config.singular} creada.`);
        setDialogOpen(false);
        setEditing(null);
      },
      onError: (e: unknown) => toast.error(extractApiError(e)),
    };
    if (editing) updateM.mutate({ id: editing.id, payload }, opts);
    else createM.mutate(payload, opts);
  }

  const data = list.data?.results ?? [];

  return (
    <div>
      <PageHeader
        title={config.title}
        description={config.description}
        actions={canWrite ? <Button onClick={onCreate}>Nuevo</Button> : null}
      />

      <div className="mb-4 flex items-center gap-2">
        <Input
          placeholder={config.searchPlaceholder ?? "Buscar…"}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:max-w-xs"
        />
        {!canWrite ? (
          <Badge variant="secondary">Solo lectura</Badge>
        ) : null}
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
            columns={columns as ColumnDef<TRead, unknown>[]}
            data={data}
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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? `Editar ${config.singular}` : `Nueva ${config.singular}`}
            </DialogTitle>
          </DialogHeader>
          <ResourceForm
            fields={config.fields}
            initial={editing as Record<string, unknown> | null}
            submitting={createM.isPending || updateM.isPending}
            onSubmit={onSubmit}
            onCancel={() => setDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      <Dialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar {config.singular}</DialogTitle>
            <DialogDescription>
              Esta acción no se puede deshacer. ¿Deseas continuar?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleting(null)}
              disabled={removeM.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={removeM.isPending}
            >
              {removeM.isPending ? "Eliminando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
