"use client";

import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { cn } from "@/lib/utils";
import type { Granularity, TimeSeriesGroup } from "@/lib/dashboard/types";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  chartColor,
  formatBucketLabel,
  usePrefersReducedMotion,
} from "@/components/dashboard/charts/chart-utils";

interface StackedAreaChartProps {
  series: TimeSeriesGroup;
  granularidad: Granularity;
  /** Resuelve la etiqueta legible de un grupo (`estado_codigo`). */
  labelFor: (group: string) => string;
}

/**
 * AreaChart multi-serie apilado por grupo (p. ej. estado). Leyenda conmutable: al hacer clic en una
 * serie se oculta/muestra. Presentacional.
 */
export function StackedAreaChart({
  series,
  granularidad,
  labelFor,
}: StackedAreaChartProps) {
  const reducedMotion = usePrefersReducedMotion();
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const config = useMemo<ChartConfig>(() => {
    const cfg: ChartConfig = {};
    series.groups.forEach((group, i) => {
      cfg[group] = { label: labelFor(group), color: chartColor(i) };
    });
    return cfg;
  }, [series.groups, labelFor]);

  const formatX = (bucket: string) => formatBucketLabel(bucket, granularidad);

  const toggle = (group: string) => {
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(group)) next.delete(group);
      else next.add(group);
      return next;
    });
  };

  return (
    <div>
      <ChartContainer config={config} className="h-[260px] w-full">
        <AreaChart accessibilityLayer data={series.rows} margin={{ left: 8, right: 8 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="bucket"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            minTickGap={24}
            tickFormatter={formatX}
          />
          <YAxis allowDecimals={false} width={40} tickLine={false} axisLine={false} />
          <ChartTooltip
            content={
              <ChartTooltipContent labelFormatter={(value) => formatX(String(value))} />
            }
          />
          {series.groups.map((group, i) => (
            <Area
              key={group}
              dataKey={group}
              type="monotone"
              stackId="actividades"
              hide={hidden.has(group)}
              fill={chartColor(i)}
              fillOpacity={0.3}
              stroke={chartColor(i)}
              strokeWidth={2}
              isAnimationActive={!reducedMotion}
            />
          ))}
        </AreaChart>
      </ChartContainer>

      {/* Leyenda conmutable (color + etiqueta; no solo color) */}
      <div className="mt-3 flex flex-wrap items-center justify-center gap-3">
        {series.groups.map((group, i) => {
          const isHidden = hidden.has(group);
          return (
            <button
              key={group}
              type="button"
              onClick={() => toggle(group)}
              aria-pressed={!isHidden}
              className={cn(
                "flex items-center gap-1.5 text-xs transition-opacity",
                isHidden ? "opacity-40" : "opacity-100",
              )}
            >
              <span
                className="size-2.5 shrink-0 rounded-[2px]"
                style={{ backgroundColor: chartColor(i) }}
              />
              {labelFor(group)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
