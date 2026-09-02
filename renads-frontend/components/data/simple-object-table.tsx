"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/** Columna de la tabla simple: clave del objeto + encabezado legible. */
export interface SimpleColumn {
  key: string;
  header: string;
  render?: (row: Record<string, unknown>) => React.ReactNode;
}

/**
 * Tabla de solo lectura para listas de objetos planos (sub-recursos de flujo: campos clínicos,
 * participantes, historial). Renderiza los valores como texto o con función de renderizado opcional.
 */
export function SimpleObjectTable({
  columns,
  rows,
  emptyMessage = "Sin registros.",
}: {
  columns: SimpleColumn[];
  rows: Record<string, unknown>[];
  emptyMessage?: string;
}) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((c) => (
              <TableHead key={c.key}>{c.header}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length ? (
            rows.map((row, i) => (
              <TableRow key={i}>
                {columns.map((c) => (
                  <TableCell key={c.key}>
                    {c.render ? c.render(row) : format(row[c.key])}
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-20 text-center">
                {emptyMessage}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}

function format(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  return String(value);
}
