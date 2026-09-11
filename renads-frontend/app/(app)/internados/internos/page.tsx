"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { internshipHooks, type InternshipRead, type InternshipWrite } from "@/lib/internados/hooks";
import { INTERNSHIP_FIELDS } from "@/lib/internados/internship-fields";
import { conventionHooks } from "@/lib/convenios/hooks";
import { extractApiError } from "@/lib/api/errors";
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
import { InternsBulkUploadDialog } from "@/components/internados/interns-bulk-upload-dialog";
import { ResourceForm } from "@/components/crud/resource-form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Campos de alta de internado con `convenio` oculto (se inyecta como valor fijo en el payload).
 * `showWhen: () => false` oculta la UI pero mantiene el valor en react-hook-form, de modo que
 * `optionsParamsFromEntity` del campo `ipress` siga funcionando (depende de `convenio`).
 */
const INTERNSHIP_DIALOG_FIELDS = INTERNSHIP_FIELDS.map((f) =>
  f.name === "convenio" ? { ...f, showWhen: () => false } : f,
);

/**
 * Listado de internos: universidad (acotada al alcance) → convenio Específico vigente → listado.
 * La universidad y el convenio se persisten en URL params (?u=&c=) para restaurar el estado al
 * volver desde la vista de detalle de un interno.
 */
export default function InternosPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Restaurar estado desde URL (?u=universidad_id&c=convenio_id)
  const initUni = searchParams.get("u") ? Number(searchParams.get("u")) : null;
  const initConv = searchParams.get("c") ? Number(searchParams.get("c")) : null;

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [convenio, setConvenio] = useState<number | null>(initConv);
  const [estado, setEstado] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const user = useAuthStore((s) => s.user);
  const canManageAnnexes = userHasRole(user, "Universidad", "Administrador RENADS", "Interno");
  const canCreate = userHasRole(user, "Universidad", "Administrador RENADS");

  const { universidad, gateUI } = useUniversityGate("Universidad", initUni);
  const createM = internshipHooks.useCreate();
  const { data: convenioData } = conventionHooks.useDetail(convenio);

  // Sincroniza universidad + convenio a URL (replace, sin nueva entrada de historial).
  useEffect(() => {
    const params = new URLSearchParams();
    if (universidad != null) params.set("u", String(universidad));
    if (convenio != null) params.set("c", String(convenio));
    const qs = params.toString();
    router.replace(qs ? `/internados/internos?${qs}` : "/internados/internos", { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [universidad, convenio]);

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
      {
        accessorKey: "estudiante",
        header: "Estudiante",
        cell: ({ row }) => (
          <span className="max-w-[280px] whitespace-normal text-justify text-xs leading-relaxed text-foreground">
            {String(row.original.estudiante ?? "—")}
          </span>
        ),
      },
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
          <div className="w-56">
            <EntityCombobox
              key={universidad ?? 0}
              endpoint="conventions"
              params={convenioParams}
              toLabel={(r) => String(r.nomenclatura ?? r.titulo ?? r.id)}
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
        {convenioData != null && (
          <div className="max-w-sm self-end pb-1">
            <p className="text-xs font-semibold text-primary">{convenioData.nomenclatura ?? "Sin nomenclatura"}</p>
            <p className="mt-0.5 text-xs text-muted-foreground leading-snug line-clamp-2">{String(convenioData.titulo ?? "")}</p>
          </div>
        )}
      </div>

      {universidad == null ? (
        <EmptyState label="Selecciona una universidad para continuar." />
      ) : convenio == null ? (
        <EmptyState label="Selecciona un convenio Específico vigente para ver y registrar sus internos." />
      ) : (
        <>
          {/* Toolbar: LEFT búsqueda+filtros, RIGHT botones */}
          <div className="mb-4 flex items-end gap-3">
            <div className="flex flex-1 flex-wrap items-end gap-3">
              <div className="grid gap-1.5">
                <Input
                  placeholder="Buscar por estudiante…"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="h-8 w-full sm:w-56"
                />
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs text-muted-foreground">Estado</Label>
                <div className="w-48">
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
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <InternsBulkUploadDialog convenioId={convenio} />
              {canCreate ? (
                <Button onClick={() => setCreateOpen(true)}>Nuevo interno</Button>
              ) : null}
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

      {/* Dialog de alta de interno — convenio fijo por el contexto (oculto en el form). */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Nuevo interno</DialogTitle>
          </DialogHeader>
          {convenio != null && (
            <ResourceForm
              key={convenio}
              fields={INTERNSHIP_DIALOG_FIELDS}
              initial={{ convenio }}
              submitting={createM.isPending}
              onCancel={() => setCreateOpen(false)}
              onSubmit={(payload) =>
                createM.mutate({ ...payload, convenio } as InternshipWrite, {
                  onSuccess: () => {
                    toast.success("Interno creado.");
                    setCreateOpen(false);
                  },
                  onError: (e) => toast.error(extractApiError(e)),
                })
              }
            />
          )}
        </DialogContent>
      </Dialog>
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
