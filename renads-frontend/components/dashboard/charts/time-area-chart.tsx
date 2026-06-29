"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";

import type { Granularity, TimeBucket } from "@/lib/dashboard/types";
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

interface TimeAreaChartProps {
  data: TimeBucket[];
  valueLabel: string;
  granularidad: Granularity;
}

/** AreaChart de una serie temporal (eje X rotulado por granularidad). Presentacional. */
export function TimeAreaChart({ data, valueLabel, granularidad }: TimeAreaChartProps) {
  const reducedMotion = usePrefersReducedMotion();

  const config: ChartConfig = {
    count: { label: valueLabel, color: chartColor(0) },
  };

  const formatX = useMemo(
    () => (bucket: string) => formatBucketLabel(bucket, granularidad),
    [granularidad],
  );

  return (
    <ChartContainer config={config} className="h-[260px] w-full">
      <AreaChart accessibilityLayer data={data} margin={{ left: 8, right: 8 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="bucket"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          minTickGap={24}
          tickFormatter={formatX}
        />
        <YAxis
          allowDecimals={false}
          width={40}
          tickLine={false}
          axisLine={false}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelFormatter={(value) => formatX(String(value))}
            />
          }
        />
        <Area
          dataKey="count"
          type="monotone"
          fill="var(--color-count)"
          fillOpacity={0.25}
          stroke="var(--color-count)"
          strokeWidth={2}
          isAnimationActive={!reducedMotion}
        />
      </AreaChart>
    </ChartContainer>
  );
}
