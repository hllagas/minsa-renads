"use client";

import { Button } from "@/components/ui/button";

/** Tamaño de página del backend (DRF PAGE_SIZE). Ver docs/backend-overview.md. */
export const PAGE_SIZE = 20;

/**
 * Controles de paginación para listas paginadas por el servidor (DRF). Usa `count` para calcular
 * el total de páginas; navega cambiando `page` (la query la dispara el hook de datos).
 */
export function DataTablePagination({
  page,
  count,
  onPageChange,
  isFetching,
}: {
  page: number;
  count: number;
  onPageChange: (page: number) => void;
  isFetching?: boolean;
}) {
  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  return (
    <div className="flex items-center justify-between gap-4 py-3 text-sm">
      <span className="text-muted-foreground">
        {count} resultado(s) · página {page} de {totalPages}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1 || isFetching}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages || isFetching}
          onClick={() => onPageChange(page + 1)}
        >
          Siguiente
        </Button>
      </div>
    </div>
  );
}
