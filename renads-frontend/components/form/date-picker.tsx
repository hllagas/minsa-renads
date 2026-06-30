"use client";

import { useState } from "react";
import { CalendarIcon } from "lucide-react";
import { format, parse } from "date-fns";
import { es } from "date-fns/locale";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const ISO_FORMAT = "yyyy-MM-dd";

function isoToDate(iso: string | null | undefined): Date | undefined {
  return iso ? parse(iso, ISO_FORMAT, new Date()) : undefined;
}
function dateToIso(date: Date | undefined): string {
  return date ? format(date, ISO_FORMAT) : "";
}

/**
 * Selector de fecha única: `Popover` + `Calendar` (shadcn / `react-day-picker`) en español.
 * Valor/`onChange` en ISO `yyyy-MM-dd` (cadena vacía = sin fecha). Sin desfase de zona horaria.
 */
export function DatePicker({
  value,
  onChange,
  id,
  placeholder = "Seleccionar fecha",
  ariaInvalid,
  className,
}: {
  value: string | null | undefined;
  onChange: (iso: string) => void;
  id?: string;
  placeholder?: string;
  ariaInvalid?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const date = isoToDate(value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            id={id}
            variant="outline"
            aria-invalid={ariaInvalid}
            className={className ?? "w-full justify-start gap-2 font-normal"}
          />
        }
      >
        <CalendarIcon className="size-4 text-muted-foreground" />
        <span className="truncate">
          {date ? (
            format(date, "d MMM yyyy", { locale: es })
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </span>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-auto p-0">
        <Calendar
          mode="single"
          locale={es}
          defaultMonth={date}
          selected={date}
          onSelect={(d: Date | undefined) => {
            onChange(dateToIso(d));
            setOpen(false);
          }}
          autoFocus
        />
      </PopoverContent>
    </Popover>
  );
}
