/**
 * Tipos locales del dashboard. Las respuestas del API se tipan con los tipos generados de OpenAPI
 * (`lib/api/schema.d.ts`); aquí solo viven los tipos de presentación/agregación del dashboard.
 * Las claves del API (estado_codigo, fecha_solicitud, ...) se mantienen en español sin traducir.
 */

/** Módulo activo de la barra de filtros (también determina la sección visible). */
export type DashboardModule = "convenios" | "internados" | "actividades";

/** Granularidad temporal de las series de tiempo. */
export type Granularity = "dia" | "mes" | "anio";

/** Estado de los filtros globales del dashboard (sincronizado a la URL). */
export interface DashboardFilters {
  /** Inicio del rango (ISO `yyyy-MM-dd`) o `null` (sin límite). */
  desde: string | null;
  /** Fin del rango (ISO `yyyy-MM-dd`) o `null` (sin límite). */
  hasta: string | null;
  modulo: DashboardModule;
  /** Tipo (id de catálogo): `tipo_convenio` o `tipo_actividad` según el módulo. */
  tipo: number | null;
  /** Entidad (id): IPRESS para internados/actividades. */
  entidad: number | null;
  /** Ámbito geográfico sanitario (id). Solo aplica a internados. */
  ambito: number | null;
  granularidad: Granularity;
}

/** Conteo agregado por clave (group-by por estado/tipo). */
export interface CountBucket {
  key: string;
  count: number;
}

/** Suma agregada por clave (p. ej. carga horaria por tipo). */
export interface SumBucket {
  key: string;
  total: number;
}

/** Punto de una serie temporal de conteo (bucket = etiqueta del periodo). */
export interface TimeBucket {
  bucket: string;
  count: number;
}

/**
 * Serie temporal multi-grupo (para áreas apiladas por estado). `rows` está lista para Recharts:
 * cada fila tiene `bucket` + una clave numérica por cada grupo presente.
 */
export interface TimeSeriesGroup {
  buckets: string[];
  groups: string[];
  rows: Array<Record<string, string | number>>;
}

/** Variación de un KPI respecto al periodo anterior equivalente. */
export interface KpiDelta {
  /** Diferencia porcentual (+/-) o `null` si no es computable (sin periodo anterior). */
  porcentaje: number | null;
  direccion: "up" | "down" | "flat";
}

/** Modelo de una tarjeta KPI. */
export interface KpiCard {
  id: string;
  titulo: string;
  /** Valor principal ya formateado (`es-PE`). */
  valor: string;
  /** Texto auxiliar opcional (p. ej. "% sobre el total"). */
  detalle?: string;
  delta: KpiDelta | null;
}
