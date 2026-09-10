"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { Pencil, Trash2 } from "lucide-react";

import type { ResourceConfig, RowAction } from "@/lib/crud/types";
import { createResourceHooks } from "@/lib/crud/hooks";
import type { WithId } from "@/lib/api/query";
import { isSuperuser, useAuthStore, userHasRole } from "@/lib/auth/store";
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
import {
  ResourceFilters,
  type FilterValues,
} from "@/components/crud/resource-filters";

const WRITE_ROLES = ["Administrador RENADS"];

/**
 * CRUD declarativo de un recurso maestro (DRF). Lista paginada/búsqueda + alta/edición en diálogo
 * + borrado. La escritura está gateada a `Administrador RENADS` (la autoridad final es el backend).
 */
export function ResourceCrud<TRead extends WithId>({
  config,
  rowActions,
  headerActions,
  fixedValues,
  cardView,
  renderCard,
  renderForm,
  dialogClassName,
  initialFilters,
  hideHeader,
}: {
  config: ResourceConfig<TRead>;
  /** Acciones por fila inyectadas por la página (p. ej. abrir el diálogo de contraseña). */
  rowActions?: RowAction<TRead>[];
  /** Acciones extra en la cabecera, junto al botón «Nuevo» (p. ej. carga masiva). */
  headerActions?: ReactNode;
  /**
   * Formulario personalizado del diálogo de alta/edición (reemplaza a `ResourceForm`). Útil para
   * controles que no encajan en el formulario declarativo (p. ej. la matriz de permisos de un rol).
   */
  renderForm?: (args: {
    editing: TRead | null;
    submitting: boolean;
    onSubmit: (payload: Record<string, unknown>) => void;
    onCancel: () => void;
  }) => ReactNode;
  /** Clase del `DialogContent` de alta/edición (por defecto `sm:max-w-2xl`). */
  dialogClassName?: string;
  /**
   * Valores fijos por alcance (p. ej. `{ universidad: 12 }` cuando el usuario tiene una sola
   * universidad): se aplican al listado (filtro) y a cada alta, y ocultan su campo/filtro en la UI
   * (no se pide lo que ya se conoce). El backend sigue siendo la autoridad del alcance.
   */
  fixedValues?: Record<string, number | string>;
  /** Renderiza el listado como grilla de tarjetas (en vez de tabla). Requiere `renderCard`. */
  cardView?: boolean;
  /** Cuerpo visual de cada tarjeta (p. ej. logo + nombre). Las acciones las añade `ResourceCrud`. */
  renderCard?: (row: TRead) => ReactNode;
  /**
   * Filtros iniciales precargados (se aplican una sola vez al montar). Al limpiar filtros se
   * restauran estos valores (no se resetea a vacío). Útil para defaults dinámicos, p. ej.
   * "Nivel académico = Pregrado" en carreras profesionales.
   */
  initialFilters?: Record<string, string>;
  /** Oculta el PageHeader interno (título + descripción). Útil cuando la página lo renderiza antes. */
  hideHeader?: boolean;
}) {
  const hooks = useMemo(
    () => createResourceHooks<TRead, Record<string, unknown>>(config.endpoint),
    [config.endpoint],
  );

  const user = useAuthStore((s) => s.user);
  // PK del recurso (numérica o textual). Recursos con PK textual (executing-units `codigo`,
  // ipress `codigo_renipress`) declaran `pkField`; el resto usa `id`.
  const pkField = config.pkField ?? "id";
  const pkOf = (row: TRead): string | number => row[pkField] as string | number;
  // `readOnly` fuerza solo lectura para cualquier rol (catálogos ya poblados en backend).
  // `requireSuperuser` añade el gating estricto a superusuario (usuarios/roles/permisos).
  const canWrite =
    !config.readOnly &&
    userHasRole(user, ...(config.writeRoles ?? WRITE_ROLES)) &&
    (!config.requireSuperuser || isSuperuser(user));
  const canCreate = canWrite && !config.disableCreate;

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filterValues, setFilterValues] = useState<FilterValues>({});
  const [editing, setEditing] = useState<TRead | null>(null);

  // Aplica `initialFilters` una sola vez, en cuanto estén disponibles.
  const appliedInitialRef = useRef(false);
  useEffect(() => {
    if (!initialFilters || appliedInitialRef.current) return;
    appliedInitialRef.current = true;
    setFilterValues(initialFilters);
  }, [initialFilters]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState<TRead | null>(null);

  // La búsqueda se aplica con retraso para no pedir al backend en cada tecla.
  const debouncedSearch = useDebouncedValue(search, 300);

  function onFilterChange(name: string, value: string) {
    setFilterValues((prev) => ({ ...prev, [name]: value }));
    setPage(1); // resetear la paginación al cambiar cualquier filtro
  }

  function onClearFilters() {
    setFilterValues(initialFilters ?? {});
    setPage(1);
  }

  // Nombres con valor fijo por alcance: se ocultan de filtros/formulario y se inyectan.
  const fixedNames = fixedValues ? Object.keys(fixedValues) : [];
  const fixedAsStrings = fixedValues
    ? Object.fromEntries(Object.entries(fixedValues).map(([k, v]) => [k, String(v)]))
    : {};
  const visibleFilters = fixedNames.length
    ? config.filters?.filter((f) => !fixedNames.includes(f.name))
    : config.filters;
  const dropFixed = (fields: typeof config.fields) =>
    fixedNames.length ? fields.filter((f) => !fixedNames.includes(f.name)) : fields;

  const list = hooks.useList({
    page,
    search: debouncedSearch,
    ordering: config.defaultOrdering ?? config.pkField ?? "id",
    filters: { ...filterValues, ...fixedAsStrings },
  });
  const createM = hooks.useCreate();
  const updateM = hooks.useUpdate();
  const removeM = hooks.useRemove();

  const hasActions = canWrite || (rowActions?.length ?? 0) > 0;

  // Botonera de acciones por fila (editar + acciones inyectadas + eliminar). Reutilizada por la
  // tabla y por la grilla de tarjetas.
  function actionButtons(row: TRead): ReactNode {
    if (!hasActions) return null;
    return (
      <div className="flex justify-end gap-2">
        {canWrite ? (
          <Button
            variant="outline"
            size="icon-sm"
            aria-label="Editar"
            title="Editar"
            onClick={() => {
              setEditing(row);
              setDialogOpen(true);
            }}
          >
            <Pencil />
          </Button>
        ) : null}
        {(rowActions ?? []).map((action) =>
          action.visible && !action.visible(row) ? null : action.render ? (
            <span key={action.key}>{action.render(row)}</span>
          ) : (
            <Button
              key={action.key}
              variant={action.variant ?? "outline"}
              size="sm"
              onClick={() => action.onClick(row)}
            >
              {action.label}
            </Button>
          ),
        )}
        {canWrite ? (
          <Button
            variant="destructive"
            size="icon-sm"
            aria-label={config.deleteActionLabel ?? "Eliminar"}
            title={config.deleteActionLabel ?? "Eliminar"}
            onClick={() => setDeleting(row)}
          >
            <Trash2 />
          </Button>
        ) : null}
      </div>
    );
  }

  const columns = useMemo<ColumnDef<TRead>[]>(() => {
    const base: ColumnDef<TRead>[] = config.columns.map((c) => ({
      accessorKey: c.key,
      header: c.header,
      cell: ({ row }) =>
        c.render ? c.render(row.original) : String(row.original[c.key] ?? "—"),
    }));
    // La columna de acciones aparece si hay escritura (editar/eliminar) o acciones por fila
    // inyectadas por la página (p. ej. la acción CONAPRES de sede docente, sin escritura CRUD).
    if (hasActions) {
      base.push({
        id: "acciones",
        header: "",
        cell: ({ row }) => actionButtons(row.original),
      });
    }
    return base;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.columns, config.deleteActionLabel, canWrite, rowActions]);

  function onCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function confirmDelete() {
    if (!deleting) return;
    removeM.mutate(pkOf(deleting), {
      onSuccess: () => {
        toast.success(
          config.deleteSuccessMessage ?? `${config.singular} eliminada.`,
        );
        setDeleting(null);
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  function onSubmit(payload: Record<string, unknown>) {
    const finalPayload = fixedValues ? { ...payload, ...fixedValues } : payload;
    const opts = {
      onSuccess: () => {
        toast.success(editing ? "Cambios guardados." : `${config.singular} creada.`);
        setDialogOpen(false);
        setEditing(null);
      },
      onError: (e: unknown) => toast.error(extractApiError(e)),
    };
    if (editing) updateM.mutate({ id: pkOf(editing), payload: finalPayload }, opts);
    else createM.mutate(finalPayload, opts);
  }

  const data = list.data?.results ?? [];

  return (
    <div className={config.containerClassName}>
      {!hideHeader && (
        <PageHeader
          title={config.title}
          description={config.description}
          actions={
            headerActions || canCreate ? (
              <div className="flex items-center gap-2">
                {headerActions}
                {canCreate ? <Button onClick={onCreate}>Nuevo</Button> : null}
              </div>
            ) : null
          }
        />
      )}
      <div className="mb-4 flex items-end gap-3">
        {/* Izquierda: búsqueda → filtros → limpiar */}
        <div className="flex flex-1 flex-wrap items-end gap-3">
          <div className="grid gap-1.5">
            <Input
              placeholder={config.searchPlaceholder ?? "Buscar…"}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="h-8 w-full sm:w-56"
            />
          </div>
          {visibleFilters?.length ? (
            <ResourceFilters
              filters={visibleFilters}
              values={filterValues}
              onChange={onFilterChange}
              onClear={onClearFilters}
            />
          ) : null}
          {!canWrite ? (
            <Badge variant="secondary">Solo lectura</Badge>
          ) : null}
        </div>
        {/* Derecha: botones de acción (solo cuando hideHeader) */}
        {hideHeader && (headerActions || canCreate) ? (
          <div className="flex shrink-0 items-center gap-2">
            {headerActions}
            {canCreate ? <Button onClick={onCreate}>Nuevo</Button> : null}
          </div>
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
      ) : cardView && renderCard ? (
        <>
          {list.isLoading ? (
            <p className="py-8 text-center text-sm text-muted-foreground">Cargando…</p>
          ) : data.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Sin resultados.
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {data.map((row) => (
                <div
                  key={String(pkOf(row))}
                  className="flex flex-col rounded-lg border bg-card p-4 shadow-sm transition-colors hover:bg-muted/30"
                >
                  <div className="flex-1">{renderCard(row)}</div>
                  {hasActions ? (
                    <div className="mt-3 border-t pt-3">{actionButtons(row)}</div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
          <DataTablePagination
            page={page}
            count={list.data?.count ?? 0}
            onPageChange={setPage}
            isFetching={list.isFetching}
          />
        </>
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
        <DialogContent className={dialogClassName ?? "sm:max-w-2xl"}>
          <DialogHeader>
            <DialogTitle>
              {editing ? `Editar ${config.singular}` : `${config.createPrefix ?? "Nuevo"} ${config.singular}`}
            </DialogTitle>
          </DialogHeader>
          {editing && config.renderEditInfo ? (
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              {config.renderEditInfo(editing)}
            </div>
          ) : null}
          {renderForm ? (
            renderForm({
              editing,
              submitting: createM.isPending || updateM.isPending,
              onSubmit,
              onCancel: () => setDialogOpen(false),
            })
          ) : (
            <ResourceForm
              fields={dropFixed(
                editing
                  ? config.editFields ?? config.fields
                  : config.createFields ?? config.fields,
              )}
              initial={editing as Record<string, unknown> | null}
              submitting={createM.isPending || updateM.isPending}
              onSubmit={onSubmit}
              onCancel={() => setDialogOpen(false)}
            />
          )}
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
            <DialogTitle>
              {config.deleteConfirmTitle ??
                `${config.deleteActionLabel ?? "Eliminar"} ${config.singular}`}
            </DialogTitle>
            <DialogDescription>
              {config.deleteConfirmDescription ??
                (config.softDelete
                  ? "Esta acción desactiva el registro; podrá reactivarse. ¿Deseas continuar?"
                  : "Esta acción no se puede deshacer. ¿Deseas continuar?")}
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
              {removeM.isPending
                ? "Procesando…"
                : config.deleteActionLabel ?? "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
