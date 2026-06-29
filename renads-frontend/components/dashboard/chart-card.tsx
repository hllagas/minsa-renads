"use client";

import type { ReactNode } from "react";
import { AlertCircleIcon, InboxIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface ChartCardProps {
  title: string;
  description?: string;
  isLoading?: boolean;
  isError?: boolean;
  /** `true` cuando no hay datos para graficar (no se muestra eje en blanco). */
  isEmpty?: boolean;
  /** Aviso de truncamiento de la Vía A (datos parciales por tope de seguridad). */
  truncated?: boolean;
  onRetry?: () => void;
  className?: string;
  children: ReactNode;
}

/**
 * Envoltura común de un gráfico: `Card` con título/descripción y los tres estados transversales
 * (carga = skeleton, vacío = "Sin datos", error = mensaje + reintento). Componente presentacional;
 * no obtiene datos.
 */
export function ChartCard({
  title,
  description,
  isLoading,
  isError,
  isEmpty,
  truncated,
  onRetry,
  className,
  children,
}: ChartCardProps) {
  return (
    <Card className={cn("h-full", className)}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {isError ? (
          <div className="flex h-[260px] flex-col items-center justify-center gap-3 text-center text-sm text-muted-foreground">
            <AlertCircleIcon className="size-6 text-destructive" />
            <p>No se pudieron cargar los datos.</p>
            {onRetry ? (
              <Button variant="outline" size="sm" onClick={onRetry}>
                Reintentar
              </Button>
            ) : null}
          </div>
        ) : isLoading ? (
          <div className="flex h-[260px] flex-col justify-end gap-2">
            <Skeleton className="h-[220px] w-full" />
          </div>
        ) : isEmpty ? (
          <div className="flex h-[260px] flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
            <InboxIcon className="size-6" />
            <p>Sin datos para el filtro seleccionado.</p>
            <p className="text-xs">Ajusta el rango de fechas u otros filtros.</p>
          </div>
        ) : (
          <>
            {children}
            {truncated ? (
              <p className="mt-2 text-xs text-muted-foreground">
                Datos parciales: se alcanzó el límite de carga. Acota el rango de fechas para mayor
                exactitud.
              </p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
