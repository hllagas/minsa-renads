import type { ReactNode } from "react";

import type { WithId } from "@/lib/api/query";

export type FieldType = "text" | "number" | "boolean" | "date" | "email" | "select";

export interface FieldConfig {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  /** Solo para `type: "select"`: endpoint DRF que provee las opciones (búsqueda server-side). */
  optionsEndpoint?: string;
  /** Filtros fijos para el endpoint de opciones (p. ej. `{ activo: "true" }`). */
  optionsParams?: Record<string, string>;
  /** Etiqueta de cada opción (por defecto `nombre`/`titulo`). */
  optionsToLabel?: (row: WithId) => string;
  /** Solo para `type: "select"`: opciones estáticas (enum). Si está, no usa endpoint. */
  choices?: { value: string; label: string }[];
  /** Valor por defecto al crear. */
  defaultValue?: string | number | boolean | null;
}

export interface ColumnConfig<T extends WithId = WithId> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
}

/** Configuración declarativa de un recurso CRUD (entidad maestra del backend). */
export interface ResourceConfig<TRead extends WithId = WithId> {
  /** Endpoint DRF, p. ej. `universities`. */
  endpoint: string;
  /** Título plural, p. ej. "Universidades". */
  title: string;
  /** Singular para diálogos, p. ej. "universidad". */
  singular: string;
  description?: string;
  columns: ColumnConfig<TRead>[];
  fields: FieldConfig[];
  searchPlaceholder?: string;
  /** Roles con permiso de escritura (por defecto solo `Administrador RENADS`). */
  writeRoles?: string[];
}
