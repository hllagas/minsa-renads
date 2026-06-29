"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  chartColor,
  usePrefersReducedMotion,
} from "@/components/dashboard/charts/chart-utils";

export interface CategoryDatum {
  label: string;
  value: number;
}

interface CategoryBarChartProps {
  data: CategoryDatum[];
  /** Dirección de las barras: `horizontal` (comparación de estados) o `vertical`. */
  orientation?: "horizontal" | "vertical";
  /** Etiqueta de la métrica (leyenda/tooltip). */
  valueLabel: string;
  /** Formateador del valor (p. ej. horas). Por defecto, entero `es-PE`. */
  valueFormatter?: (value: number) => string;
}

const defaultFormatter = (v: number) => v.toLocaleString("es-PE");

/** BarChart de una sola serie para comparar categorías (estados/tipos). Presentacional. */
export function CategoryBarChart({
  data,
  orientation = "horizontal",
  valueLabel,
  valueFormatter = defaultFormatter,
}: CategoryBarChartProps) {
  const reducedMotion = usePrefersReducedMotion();
  const config: ChartConfig = {
    value: { label: valueLabel, color: chartColor(0) },
  };

  return (
    <ChartContainer config={config} className="h-[260px] w-full">
      {orientation === "horizontal" ? (
        <BarChart
          accessibilityLayer
          data={data}
          layout="vertical"
          margin={{ left: 8, right: 16 }}
        >
          <CartesianGrid horizontal={false} />
          <XAxis type="number" tickFormatter={valueFormatter} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="label"
            width={120}
            tickLine={false}
            axisLine={false}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value) => (
                  <span className="font-mono font-medium tabular-nums">
                    {valueFormatter(Number(value))}
                  </span>
                )}
              />
            }
          />
          <Bar
            dataKey="value"
            fill="var(--color-value)"
            radius={4}
            isAnimationActive={!reducedMotion}
          />
        </BarChart>
      ) : (
        <BarChart accessibilityLayer data={data} margin={{ left: 8, right: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis tickFormatter={valueFormatter} allowDecimals={false} width={48} />
          <ChartTooltip
            content={
              <ChartTooltipContent
                formatter={(value) => (
                  <span className="font-mono font-medium tabular-nums">
                    {valueFormatter(Number(value))}
                  </span>
                )}
              />
            }
          />
          <Bar
            dataKey="value"
            fill="var(--color-value)"
            radius={4}
            isAnimationActive={!reducedMotion}
          />
        </BarChart>
      )}
    </ChartContainer>
  );
}
