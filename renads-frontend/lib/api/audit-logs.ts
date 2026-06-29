"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type Paginated } from "@/lib/api/client";
import { buildListParams, resourceKeys, type HasId, type ListParams } from "@/lib/api/query";

const ENDPOINT = "audit-logs";
const base = `/${ENDPOINT}/`;

/** Registro de bitácora de auditoría (solo lectura). Campos del contrato (§5). */
export interface AuditLog extends HasId {
  id: number;
  usuario: number | null;
  usuario_nombre: string;
  accion: string;
  tipo_contenido: number | null;
  tipo_contenido_label: string;
  id_objeto: number | null;
  nombre_campo: string | null;
  valor_anterior: string | null;
  valor_nuevo: string | null;
  direccion_ip: string | null;
  creado_en: string;
}

/**
 * Filtros de `audit-logs` (según `AuditLogFilter` del backend, ver §5/R3): exactos
 * `usuario`/`accion`/`tipo_contenido`/`id_objeto`, `accion_contiene` (icontains) y rango de fechas
 * `creado_en_desde`/`creado_en_hasta`.
 */
export interface AuditLogFilters {
  usuario?: string;
  accion?: string;
  accion_contiene?: string;
  tipo_contenido?: string;
  id_objeto?: string;
  creado_en_desde?: string;
  creado_en_hasta?: string;
}

/** Cliente Axios del recurso de solo lectura `audit-logs` (solo en `lib/api/`). */
export const auditLogsApi = {
  async list(params: ListParams = {}): Promise<Paginated<AuditLog>> {
    const { data } = await api.get<Paginated<AuditLog>>(base, {
      params: buildListParams(params),
    });
    return data;
  },
  async retrieve(id: number): Promise<AuditLog> {
    const { data } = await api.get<AuditLog>(`${base}${id}/`);
    return data;
  },
};

/** Lista paginada de la bitácora (solo lectura). Orden por defecto `creado_en` desc. */
export function useAuditLogsList(params: ListParams = {}) {
  return useQuery({
    queryKey: resourceKeys.list(ENDPOINT, params),
    queryFn: () => auditLogsApi.list(params),
  });
}
