"use client";

import { useState } from "react";
import { CalendarIcon } from "lucide-react";
import { format, parse } from "date-fns";
import { es } from "date-fns/locale";
import type { DateRange as RdpDateRange } from "react-day-picker";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

/** Rango de salida del control: fechas en ISO `yyyy-MM-dd` o `null`. API pública estable. */
export interface DateRange {
  desde: string | null;
  hasta: string | null;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

/** Formato ISO de fecha (sin componente horario), usado por el backend y la URL. */
const ISO_FORMAT = "yyyy-MM-dd";

/** Fecha local de hoy en ISO `yyyy-MM-dd` (sin desfase de zona horaria). */
function localTodayIso(): string {
  return format(new Date(), ISO_FORMAT);
}

function shiftIso(iso: string, days: number): string {
  const date = parse(iso, ISO_FORMAT, new Date());
  date.setDate(date.getDate() + days);
  return format(date, ISO_FORMAT);
}

/** ISO `yyyy-MM-dd` → `Date` local (sin saltos de zona horaria). */
function isoToDate(iso: string | null): Date | undefined {
  if (!iso) return undefined;
  return parse(iso, ISO_FORMAT, new Date());
}

/** `Date` → ISO `yyyy-MM-dd`. */
function dateToIso(date: Date | undefined): string | null {
  return date ? format(date, ISO_FORMAT) : null;
}

/** Etiqueta legible en español de una fecha ISO. */
function formatIso(iso: string | null): string {
  const date = isoToDate(iso);
  return date ? format(date, "d MMM yyyy", { locale: es }) : "—";
}

/** Texto del botón disparador según el rango activo. */
function rangeLabel({ desde, hasta }: DateRange): string {
  if (!desde && !hasta) return "Todo el periodo";
  return `${formatIso(desde)} – ${formatIso(hasta)}`;
}

/**
 * Selector de rango de fechas: `Popover` + `Calendar` (shadcn / `react-day-picker`) en modo rango,
 * con preajustes rápidos y localización en español. Devuelve `{ desde, hasta }` en ISO `yyyy-MM-dd`
 * o `null`. Se cierra automáticamente al elegir el segundo extremo del rango.
 */
export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const today = localTodayIso();

  const selected: RdpDateRange | undefined = value.desde
    ? { from: isoToDate(value.desde), to: isoToDate(value.hasta) }
    : undefined;

  const applyPreset = (range: DateRange) => {
    onChange(range);
    setOpen(false);
  };

  const handleSelect = (range: RdpDateRange | undefined) => {
    onChange({
      desde: dateToIso(range?.from),
      hasta: dateToIso(range?.to),
    });
    // Cerrar al completar el segundo extremo del rango.
    if (range?.from && range?.to) {
      setOpen(false);
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button variant="outline" className="w-full justify-start gap-2 sm:w-64" />
        }
        aria-label={`Rango de fechas: ${rangeLabel(value)}`}
      >
        <CalendarIcon className="size-4 text-muted-foreground" />
        <span className="truncate">{rangeLabel(value)}</span>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-auto p-0">
        <div className="flex flex-wrap gap-2 border-b p-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => applyPreset({ desde: shiftIso(today, -29), hasta: today })}
          >
            Últimos 30 días
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() =>
              applyPreset({ desde: `${today.slice(0, 4)}-01-01`, hasta: today })
            }
          >
            Este año
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => applyPreset({ desde: null, hasta: null })}
          >
            Todo
          </Button>
        </div>

        <Calendar
          mode="range"
          locale={es}
          numberOfMonths={2}
          defaultMonth={isoToDate(value.desde)}
          selected={selected}
          onSelect={handleSelect}
          autoFocus
        />
      </PopoverContent>
    </Popover>
  );
}
