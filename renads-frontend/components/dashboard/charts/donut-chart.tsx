"use client";

import { useMemo } from "react";
import { Cell, Label, Pie, PieChart } from "recharts";

import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  chartColor,
  usePrefersReducedMotion,
} from "@/components/dashboard/charts/chart-utils";

export interface DonutDatum {
  /** Clave estable de la categoría (código o etiqueta). */
  key: string;
  /** Etiqueta legible. */
  label: string;
  value: number;
}

interface DonutChartProps {
  data: DonutDatum[];
  /** Texto central (total). */
  totalLabel?: string;
}

/** PieChart en modo donut para proporciones por categoría. Presentacional. */
export function DonutChart({ data, totalLabel = "Total" }: DonutChartProps) {
  const reducedMotion = usePrefersReducedMotion();

  const total = useMemo(() => data.reduce((acc, d) => acc + d.value, 0), [data]);

  const config = useMemo<ChartConfig>(() => {
    const cfg: ChartConfig = {};
    data.forEach((d, i) => {
      cfg[d.key] = { label: d.label, color: chartColor(i) };
    });
    return cfg;
  }, [data]);

  const chartData = useMemo(
    () => data.map((d, i) => ({ ...d, fill: chartColor(i) })),
    [data],
  );

  return (
    <ChartContainer config={config} className="mx-auto h-[260px] w-full">
      <PieChart>
        <ChartTooltip
          content={
            <ChartTooltipContent
              nameKey="key"
              hideLabel
              formatter={(value, _name, item) => {
                const v = Number(value) || 0;
                const pct = total > 0 ? (v / total) * 100 : 0;
                const raw = item.payload as
                  | (DonutDatum & { fill: string })
                  | undefined;
                return (
                  <div className="flex w-full items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-[2px]"
                      style={{ background: raw?.fill }}
                    />
                    <span className="text-muted-foreground">{raw?.label}</span>
                    <span className="ml-auto font-medium text-foreground tabular-nums">
                      {v.toLocaleString("es-PE")} ({pct.toFixed(1)}%)
                    </span>
                  </div>
                );
              }}
            />
          }
        />
        <Pie
          data={chartData}
          dataKey="value"
          nameKey="key"
          innerRadius={60}
          strokeWidth={2}
          isAnimationActive={!reducedMotion}
        >
          {chartData.map((d) => (
            <Cell key={d.key} fill={d.fill} />
          ))}
          <Label
            content={({ viewBox }) => {
              if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                return (
                  <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle">
                    <tspan
                      x={viewBox.cx}
                      y={viewBox.cy}
                      className="fill-foreground text-2xl font-bold"
                    >
                      {total.toLocaleString("es-PE")}
                    </tspan>
                    <tspan
                      x={viewBox.cx}
                      y={(viewBox.cy ?? 0) + 20}
                      className="fill-muted-foreground text-xs"
                    >
                      {totalLabel}
                    </tspan>
                  </text>
                );
              }
              return null;
            }}
          />
        </Pie>
        <ChartLegend content={<ChartLegendContent nameKey="key" />} />
      </PieChart>
    </ChartContainer>
  );
}
