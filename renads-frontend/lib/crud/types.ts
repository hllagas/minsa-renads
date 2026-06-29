import type { ReactNode } from "react";

import type { WithId } from "@/lib/api/query";

export type FieldType =
  | "text"
  | "number"
  | "boolean"
  | "date"
  | "email"
  | "select"
  | "password"
  | "multiselect";

export interface FieldConfig {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  /** Para `type: "select"`/`"multiselect"`: endpoint DRF que provee las opciones (búsqueda server-side). */
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

/** Variantes de botón admitidas por las acciones por fila (subconjunto de `Button`). */
export type RowActionVariant =
  | "default"
  | "outline"
  | "secondary"
  | "destructive"
  | "ghost";

/**
 * Acción por fila inyectada por la página que monta `ResourceCrud` (no es data; vive en el
 * componente). El estado/diálogo asociado lo posee la página (p. ej. el diálogo de contraseña).
 */
export interface RowAction<TRead extends WithId = WithId> {
  key: string;
  label: string;
  variant?: RowActionVariant;
  /** Render personalizado del botón/control (si se omite, se usa un `Button` estándar). */
  render?: (row: TRead) => ReactNode;
  onClick: (row: TRead) => void;
  /** Condiciona la visibilidad de la acción para una fila concreta. */
  visible?: (row: TRead) => boolean;
}

/** Tipo de control de un filtro de listado declarativo. */
export type FilterType = "select" | "boolean" | "text";

/**
 * Filtro declarativo de un listado (mapea a los `filterset_fields` de django-filter del backend).
 * Reutiliza la forma de `FieldConfig` para los selects (FK por endpoint o enum por `choices`).
 */
export interface FilterConfig {
  /** Nombre exacto del query param del backend (p. ej. `universidad`, `activo`). */
  name: string;
  label: string;
  type: FilterType;
  /** Solo `type: "select"` sin `choices`: endpoint DRF que provee las opciones (FK). */
  optionsEndpoint?: string;
  /** Filtros fijos para el endpoint de opciones (p. ej. `{ activo: "true" }`). */
  optionsParams?: Record<string, string>;
  /** Etiqueta de cada opción del select FK. */
  optionsToLabel?: (row: WithId) => string;
  /** Solo `type: "select"`: opciones estáticas (enum). Si está, no usa endpoint. */
  choices?: { value: string; label: string }[];
  /** Placeholder para filtros de texto. */
  placeholder?: string;
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
  /** Campos del formulario (fallback común para alta y edición). */
  fields: FieldConfig[];
  /** Campos solo para el alta (si se omite, se usa `fields`). P. ej. usuario con `password`. */
  createFields?: FieldConfig[];
  /** Campos solo para la edición (si se omite, se usa `fields`). P. ej. usuario sin `password`. */
  editFields?: FieldConfig[];
  searchPlaceholder?: string;
  /** Filtros declarativos (django-filter). Se aplican vía `ListParams.filters`. */
  filters?: FilterConfig[];
  /** Orden por defecto del listado (DRF `ordering`). Por defecto `id`. */
  defaultOrdering?: string;
  /** Roles con permiso de escritura (por defecto solo `Administrador RENADS`). */
  writeRoles?: string[];
  /** Solo lectura explícito: oculta toda acción de escritura para cualquier rol. */
  readOnly?: boolean;
  /** Oculta la acción "Nuevo" conservando editar/eliminar (p. ej. alta diferida a v2). */
  disableCreate?: boolean;
  /**
   * Exige superusuario (`es_superusuario`) además de `writeRoles` para escribir/crear.
   * El gating del front es UX; el backend (`IsSuperUser`) es la autoridad final.
   */
  requireSuperuser?: boolean;
  /** Baja lógica: el `DELETE` desactiva el registro (no lo borra). Cambia copy de confirmación. */
  softDelete?: boolean;
  /** Etiqueta del botón de borrado (por defecto "Eliminar"; p. ej. "Desactivar"). */
  deleteActionLabel?: string;
  /** Título del diálogo de borrado (por defecto `${acción} ${singular}`). */
  deleteConfirmTitle?: string;
  /** Descripción del diálogo de borrado (sobrescribe el texto por defecto). */
  deleteConfirmDescription?: string;
  /** Mensaje de éxito tras borrar (por defecto `${singular} eliminada.`). */
  deleteSuccessMessage?: string;
  /** Contenido de solo lectura mostrado encima del formulario al editar (no al crear). */
  renderEditInfo?: (row: TRead) => ReactNode;
}
