"use client";

import { ArrowDownIcon, ArrowRightIcon, ArrowUpIcon } from "lucide-react";

import type { DashboardFilters } from "@/lib/dashboard/types";
import { useKpis } from "@/lib/dashboard/hooks";
import type { KpiCard as KpiCardModel } from "@/lib/dashboard/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const percentFormatter = new Intl.NumberFormat("es-PE", {
  maximumFractionDigits: 1,
  signDisplay: "always",
});

function DeltaBadge({ delta }: { delta: KpiCardModel["delta"] }) {
  if (!delta || delta.porcentaje == null) {
    return (
      <Badge variant="ghost" className="text-muted-foreground">
        Sin comparación
      </Badge>
    );
  }
  const { direccion, porcentaje } = delta;
  const Icon =
    direccion === "up" ? ArrowUpIcon : direccion === "down" ? ArrowDownIcon : ArrowRightIcon;
  const variant =
    direccion === "up" ? "default" : direccion === "down" ? "destructive" : "secondary";
  const texto =
    direccion === "flat" ? "Sin cambios" : `${percentFormatter.format(porcentaje)} %`;
  return (
    <Badge variant={variant}>
      <Icon />
      <span>{texto}</span>
    </Badge>
  );
}

/** Fila de 4 tarjetas KPI (métrica grande + variación vs. periodo anterior). */
export function KpiCards({ filters }: { filters: DashboardFilters }) {
  const { cards, isLoading, isError, refetch } = useKpis(filters);

  if (isError) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-8 text-center text-sm text-muted-foreground">
          <p>No se pudieron cargar los indicadores.</p>
          <Button variant="outline" size="sm" onClick={refetch}>
            Reintentar
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.id}>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {card.titulo}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? (
              <>
                <Skeleton className="h-8 w-24" />
                <Skeleton className="h-5 w-20" />
              </>
            ) : (
              <>
                <div className="text-3xl font-bold tabular-nums">
                  {card.valor || "—"}
                </div>
                <div className="flex items-center gap-2">
                  <DeltaBadge delta={card.delta} />
                  {card.detalle ? (
                    <span className="text-xs text-muted-foreground">{card.detalle}</span>
                  ) : null}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
