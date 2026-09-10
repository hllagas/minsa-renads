"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { Eye, Download, Trash2 } from "lucide-react";

import {
  useDocumentsList,
  useRemoveDocument,
  useDocumentDownloadUrl,
  type Documento,
} from "@/lib/api/documents";
import type { FilterConfig } from "@/lib/crud/types";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { DataTable } from "@/components/ui/data-table";
import { DataTablePagination } from "@/components/data/data-table-pagination";
import {
  ResourceFilters,
  type FilterValues,
} from "@/components/crud/resource-filters";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// Filtros reales del contrato (§4). `tipo_contenido`/`id_objeto` son ids (no hay endpoint de
// content-types → se filtran por id como texto); `tipo_documento` es FK a `document-types`.
const FILTERS: FilterConfig[] = [
  { name: "tipo_documento", label: "Tipo de documento", type: "select", optionsEndpoint: "document-types" },
  { name: "estado", label: "Estado", type: "text", placeholder: "ACTIVO…" },
  { name: "tipo_contenido", label: "Tipo de entidad (id)", type: "text", placeholder: "ContentType id" },
  { name: "id_objeto", label: "Objeto (id)", type: "text", placeholder: "id del objeto" },
];

/** Documentos — v1: list + filtros + descargar + eliminar. El alta queda diferida a v2 (content-types). */
export default function DocumentosPage() {
  const [page, setPage] = useState(1);
  const [filterValues, setFilterValues] = useState<FilterValues>({});
  const [deleting, setDeleting] = useState<Documento | null>(null);
  // Documento en previsualización (URL firmada resuelta) para verlo dentro de la app.
  const [viewing, setViewing] = useState<{ doc: Documento; url: string } | null>(null);

  const list = useDocumentsList({ page, filters: filterValues });
  const removeM = useRemoveDocument();
  const downloadM = useDocumentDownloadUrl();

  function onFilterChange(name: string, value: string) {
    setFilterValues((prev) => ({ ...prev, [name]: value }));
    setPage(1);
  }

  function onDownload(doc: Documento) {
    downloadM.mutate(doc.id, {
      onSuccess: ({ url }) => window.open(url, "_blank", "noopener,noreferrer"),
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  /** Resuelve la URL firmada y muestra el documento dentro de la app (previsualización). */
  function onView(doc: Documento) {
    downloadM.mutate(doc.id, {
      onSuccess: ({ url }) => setViewing({ doc, url }),
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  function confirmDelete() {
    if (!deleting) return;
    removeM.mutate(deleting.id, {
      onSuccess: () => {
        toast.success("Documento eliminado.");
        setDeleting(null);
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  const columns = useMemo<ColumnDef<Documento>[]>(
    () => [
      { accessorKey: "tipo_documento_nombre", header: "Tipo", cell: ({ row }) => row.original.tipo_documento_nombre || "—" },
      { accessorKey: "nombre_archivo", header: "Archivo" },
      {
        id: "destino",
        header: "Destino",
        cell: ({ row }) => `${row.original.tipo_contenido_label} #${row.original.id_objeto}`,
      },
      { accessorKey: "version", header: "Versión" },
      { accessorKey: "estado", header: "Estado" },
      {
        accessorKey: "cargado_en",
        header: "Cargado",
        cell: ({ row }) => row.original.cargado_en?.slice(0, 10) ?? "—",
      },
      {
        id: "acciones",
        header: "",
        cell: ({ row }) => (
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Ver"
              title="Ver"
              onClick={() => onView(row.original)}
              disabled={downloadM.isPending}
            >
              <Eye />
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Descargar"
              title="Descargar"
              onClick={() => onDownload(row.original)}
              disabled={downloadM.isPending}
            >
              <Download />
            </Button>
            <Button
              variant="destructive"
              size="icon-sm"
              aria-label="Eliminar"
              title="Eliminar"
              onClick={() => setDeleting(row.original)}
            >
              <Trash2 />
            </Button>
          </div>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [downloadM.isPending],
  );

  return (
    <div>
      <div className="mb-4">
        <Link href="/catalogos" className="text-sm text-muted-foreground hover:text-foreground">
          ← Catálogos
        </Link>
      </div>

      <PageHeader
        title="Documentos"
        description="Gestión documental polimórfica con versionado. El alta de documentos se habilitará en una próxima versión."
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <ResourceFilters
          filters={FILTERS}
          values={filterValues}
          onChange={onFilterChange}
          onClear={() => {
            setFilterValues({});
            setPage(1);
          }}
        />
      </div>

      {list.isError ? (
        <div className="flex flex-col items-start gap-3 rounded-md border border-destructive/30 p-4">
          <p className="text-sm text-destructive">No se pudo cargar el listado.</p>
          <Button variant="outline" size="sm" onClick={() => list.refetch()} disabled={list.isFetching}>
            {list.isFetching ? "Reintentando…" : "Reintentar"}
          </Button>
        </div>
      ) : (
        <>
          <DataTable
            columns={columns as ColumnDef<Documento, unknown>[]}
            data={list.data?.results ?? []}
            isLoading={list.isLoading}
            emptyMessage="Sin documentos."
          />
          <DataTablePagination
            page={page}
            count={list.data?.count ?? 0}
            onPageChange={setPage}
            isFetching={list.isFetching}
          />
        </>
      )}

      <Dialog open={viewing !== null} onOpenChange={(open) => !open && setViewing(null)}>
        <DialogContent className="flex h-[85vh] w-[95vw] max-w-5xl flex-col sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle className="truncate pr-8">
              {viewing?.doc.nombre_archivo ?? "Documento"}
            </DialogTitle>
            <DialogDescription>
              {viewing
                ? `${viewing.doc.tipo_documento_nombre || "Documento"} · versión ${viewing.doc.version}`
                : ""}
            </DialogDescription>
          </DialogHeader>
          {viewing ? (
            <iframe
              key={viewing.url}
              src={viewing.url}
              title={viewing.doc.nombre_archivo}
              className="min-h-0 w-full flex-1 rounded-md border bg-muted"
            />
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              render={
                viewing ? (
                  <a href={viewing.url} target="_blank" rel="noopener noreferrer">
                    Abrir en pestaña nueva
                  </a>
                ) : undefined
              }
            />
            <Button variant="outline" onClick={() => setViewing(null)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar documento</DialogTitle>
            <DialogDescription>
              Esta acción no se puede deshacer. ¿Deseas continuar?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleting(null)} disabled={removeM.isPending}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={removeM.isPending}>
              {removeM.isPending ? "Eliminando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
