/**
 * Helpers puros de agregación en cliente para la "Vía A" del dashboard (sin endpoints `/stats/`).
 * Sin dependencias de React. Manejan listas vacías devolviendo `[]` (nunca `undefined`).
 */

import type {
  CountBucket,
  Granularity,
  SumBucket,
  TimeBucket,
  TimeSeriesGroup,
} from "@/lib/dashboard/types";

/**
 * Reduce una lista de buckets de conteo a los `max` mayores, agrupando el resto en una categoría
 * "Otros" (para mantener legible un donut con muchas categorías). Conserva el orden por conteo.
 */
export function topNWithOther(
  buckets: CountBucket[],
  max: number,
  otherKey = "Otros",
): CountBucket[] {
  if (buckets.length <= max) return buckets;
  const sorted = [...buckets].sort((a, b) => b.count - a.count);
  const top = sorted.slice(0, max);
  const rest = sorted.slice(max).reduce((acc, b) => acc + b.count, 0);
  if (rest > 0) top.push({ key: otherKey, count: rest });
  return top;
}

/** Conteo group-by por la clave que devuelve `keyFn`. Omite items cuya clave sea vacía/nula. */
export function countBy<T>(
  items: readonly T[],
  keyFn: (item: T) => string | null | undefined,
): CountBucket[] {
  const map = new Map<string, number>();
  for (const item of items) {
    const key = keyFn(item);
    if (key == null || key === "") continue;
    map.set(key, (map.get(key) ?? 0) + 1);
  }
  return [...map.entries()].map(([key, count]) => ({ key, count }));
}

/** Suma group-by: agrupa por `keyFn` y suma `valueFn` (valores no finitos cuentan como 0). */
export function sumBy<T>(
  items: readonly T[],
  keyFn: (item: T) => string | null | undefined,
  valueFn: (item: T) => number,
): SumBucket[] {
  const map = new Map<string, number>();
  for (const item of items) {
    const key = keyFn(item);
    if (key == null || key === "") continue;
    const raw = valueFn(item);
    const value = Number.isFinite(raw) ? raw : 0;
    map.set(key, (map.get(key) ?? 0) + value);
  }
  return [...map.entries()].map(([key, total]) => ({ key, total }));
}

// --- Series de tiempo -------------------------------------------------------

/** Normaliza una fecha ISO/`yyyy-MM-dd...` a la clave de su bucket según la granularidad. */
export function bucketKey(dateIso: string, granularidad: Granularity): string {
  const ymd = dateIso.slice(0, 10); // yyyy-MM-dd
  if (granularidad === "anio") return ymd.slice(0, 4);
  if (granularidad === "mes") return ymd.slice(0, 7);
  return ymd;
}

/** Devuelve la clave del bucket siguiente (para rellenar huecos del eje). */
function nextBucketKey(key: string, granularidad: Granularity): string {
  if (granularidad === "anio") {
    return String(Number(key) + 1);
  }
  if (granularidad === "mes") {
    const [y, m] = key.split("-").map(Number);
    const date = new Date(Date.UTC(y, m - 1 + 1, 1));
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
  }
  const [y, m, d] = key.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + 1));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(
    date.getUTCDate(),
  ).padStart(2, "0")}`;
}

/** Enumera todas las claves de bucket entre `min` y `max` (inclusive), sin huecos. */
function enumerateBuckets(
  min: string,
  max: string,
  granularidad: Granularity,
): string[] {
  const out: string[] = [];
  let cursor = min;
  // Tope defensivo para evitar bucles si los datos son inconsistentes.
  for (let i = 0; i < 5000 && cursor <= max; i++) {
    out.push(cursor);
    if (cursor === max) break;
    cursor = nextBucketKey(cursor, granularidad);
  }
  return out;
}

/**
 * Serie temporal de conteo ordenada y sin huecos: los buckets vacíos dentro del rango de datos se
 * rellenan con `count: 0`. Items con fecha vacía/nula se ignoran.
 */
export function timeSeries<T>(
  items: readonly T[],
  dateFn: (item: T) => string | null | undefined,
  granularidad: Granularity,
): TimeBucket[] {
  const counts = new Map<string, number>();
  for (const item of items) {
    const date = dateFn(item);
    if (!date) continue;
    const key = bucketKey(date, granularidad);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  if (counts.size === 0) return [];
  const keys = [...counts.keys()].sort();
  const all = enumerateBuckets(keys[0], keys[keys.length - 1], granularidad);
  return all.map((bucket) => ({ bucket, count: counts.get(bucket) ?? 0 }));
}

/**
 * Serie temporal multi-grupo (una serie por valor de `groupFn`). Devuelve filas listas para
 * Recharts: `{ bucket, [grupo]: count }` con buckets sin huecos y ceros en grupos ausentes.
 */
export function timeSeriesByGroup<T>(
  items: readonly T[],
  dateFn: (item: T) => string | null | undefined,
  groupFn: (item: T) => string | null | undefined,
  granularidad: Granularity,
): TimeSeriesGroup {
  const groups = new Set<string>();
  // bucket -> grupo -> count
  const matrix = new Map<string, Map<string, number>>();
  for (const item of items) {
    const date = dateFn(item);
    const group = groupFn(item);
    if (!date || group == null || group === "") continue;
    groups.add(group);
    const key = bucketKey(date, granularidad);
    const row = matrix.get(key) ?? new Map<string, number>();
    row.set(group, (row.get(group) ?? 0) + 1);
    matrix.set(key, row);
  }
  if (matrix.size === 0) {
    return { buckets: [], groups: [], rows: [] };
  }
  const keys = [...matrix.keys()].sort();
  const buckets = enumerateBuckets(keys[0], keys[keys.length - 1], granularidad);
  const groupList = [...groups].sort();
  const rows = buckets.map((bucket) => {
    const row: Record<string, string | number> = { bucket };
    const data = matrix.get(bucket);
    for (const group of groupList) {
      row[group] = data?.get(group) ?? 0;
    }
    return row;
  });
  return { buckets, groups: groupList, rows };
}

// --- Filtros de fecha (cliente) ---------------------------------------------

/** Indica si una fecha ISO cae dentro de `[desde, hasta]` (extremos opcionales, inclusive). */
export function isWithinRange(
  dateIso: string | null | undefined,
  desde: string | null,
  hasta: string | null,
): boolean {
  if (!dateIso) return false;
  const ymd = dateIso.slice(0, 10);
  if (desde && ymd < desde) return false;
  if (hasta && ymd > hasta) return false;
  return true;
}

/** Suma `days` (puede ser negativo) a una fecha `yyyy-MM-dd` y devuelve la nueva en el mismo formato. */
export function addDaysIso(iso: string, days: number): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(
    date.getUTCDate(),
  ).padStart(2, "0")}`;
}

/**
 * Periodo inmediatamente anterior de la misma duración que `[desde, hasta]` (para la variación de
 * los KPIs). Devuelve `null` si el rango está incompleto (sin periodo de comparación).
 */
export function previousRange(
  desde: string | null,
  hasta: string | null,
): { desde: string; hasta: string } | null {
  if (!desde || !hasta) return null;
  const start = Date.UTC(
    ...(desde.split("-").map(Number) as [number, number, number]),
  );
  const end = Date.UTC(
    ...(hasta.split("-").map(Number) as [number, number, number]),
  );
  const lengthDays = Math.round((end - start) / 86_400_000) + 1;
  const prevHasta = addDaysIso(desde, -1);
  const prevDesde = addDaysIso(prevHasta, -(lengthDays - 1));
  return { desde: prevDesde, hasta: prevHasta };
}
