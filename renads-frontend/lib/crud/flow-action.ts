import type { FieldConfig } from "@/lib/crud/types";

/** Una acción de flujo de un recurso: sub-endpoint, rol(es) requerido(s) y campos de su payload. */
export interface FlowAction {
  /** Sub-ruta del endpoint (`/{endpoint}/{id}/<key>/`). */
  key: string;
  label: string;
  /** Roles que pueden ejecutarla (la autoridad final es el backend). */
  roles: string[];
  fields: FieldConfig[];
  /** Condición extra de visibilidad (p. ej. solo convenios Específicos). */
  onlyEspecifico?: boolean;
}
