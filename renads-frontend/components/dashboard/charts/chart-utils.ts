"use client";

import { useEffect, useState } from "react";

import type { Granularity } from "@/lib/dashboard/types";

/** Colores de serie desde los tokens del tema (`--chart-1..5`), ciclados. */
export const CHART_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
] as const;

/** Color de serie por índice (cicla los 5 tokens del tema). */
export function chartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}

const MONTHS_ES = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];

/** Formatea la clave de un bucket de tiempo según la granularidad (etiquetas en `es-PE`). */
export function formatBucketLabel(bucket: string, granularidad: Granularity): string {
  if (granularidad === "anio") return bucket;
  if (granularidad === "mes") {
    const [y, m] = bucket.split("-").map(Number);
    return `${MONTHS_ES[(m ?? 1) - 1]} ${y}`;
  }
  const [, m, d] = bucket.split("-").map(Number);
  return `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}`;
}

/**
 * Indica si el usuario prefiere movimiento reducido (`prefers-reduced-motion`). Sirve para
 * desactivar las animaciones de entrada de los gráficos.
 */
export function usePrefersReducedMotion(): boolean {
  // Init perezoso (lee la media query en cliente); el efecto solo suscribe cambios.
  const [reduced, setReduced] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}
