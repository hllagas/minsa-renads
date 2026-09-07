"use client";

import { useMemo, useState } from "react";
import { CalendarIcon } from "lucide-react";
import { format, isValid, parse } from "date-fns";
import { es } from "date-fns/locale";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const ISO_FORMAT = "yyyy-MM-dd";
const DISPLAY_FORMAT = "dd/MM/yyyy";

function isoToDate(iso: string | null | undefined): Date | undefined {
  if (!iso) return undefined;
  const d = parse(iso, ISO_FORMAT, new Date());
  return isValid(d) ? d : undefined;
}
function dateToIso(date: Date | undefined): string {
  return date && isValid(date) ? format(date, ISO_FORMAT) : "";
}
function dateToDisplay(date: Date | undefined): string {
  return date && isValid(date) ? format(date, DISPLAY_FORMAT) : "";
}

/**
 * Enmascara la entrada manual al formato `dd/MM/yyyy`: descarta no-dígitos, limita a 8 cifras e
 * inserta las barras automáticamente conforme se escribe (2→`dd/`, 4→`dd/MM/`). Así el usuario no
 * puede romper el formato al tipear.
 */
function maskDate(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  const parts = [digits.slice(0, 2)];
  if (digits.length > 2) parts.push(digits.slice(2, 4));
  if (digits.length > 4) parts.push(digits.slice(4, 8));
  return parts.join("/");
}

/**
 * Selector de fecha (patrón «input calendar» de shadcn): un `Input` donde se puede **escribir**
 * la fecha (`dd/MM/yyyy`) más un `Popover` + `Calendar` (react-day-picker) con navegación por
 * **desplegables de mes/año** — clave para fechas lejanas (p. ej. nacimiento). El valor y
 * `onChange` viajan en ISO `yyyy-MM-dd` (cadena vacía = sin fecha), sin desfase de zona horaria.
 */
export function DatePicker({
  value,
  onChange,
  id,
  placeholder = "dd/mm/aaaa",
  ariaInvalid,
  disabled,
  className,
}: {
  value: string | null | undefined;
  onChange: (iso: string) => void;
  id?: string;
  placeholder?: string;
  ariaInvalid?: boolean;
  disabled?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const date = useMemo(() => isoToDate(value), [value]);
  // Texto editable del input. Se resincroniza cuando el valor ISO cambia desde fuera (RHF/reset)
  // ajustando estado durante el render (patrón recomendado por React; sin efecto).
  const [text, setText] = useState<string>(() => dateToDisplay(date));
  const [lastIso, setLastIso] = useState<string>(value ?? "");
  if ((value ?? "") !== lastIso) {
    setLastIso(value ?? "");
    setText(dateToDisplay(date));
  }

  // Rango de años navegable: pasado amplio (nacimientos) y algo de futuro (fechas de internado).
  const startMonth = useMemo(() => new Date(1940, 0), []);
  const endMonth = useMemo(() => new Date(new Date().getFullYear() + 10, 11), []);

  function commitText(raw: string) {
    const trimmed = raw.trim();
    if (trimmed === "") {
      onChange("");
      return;
    }
    // Solo se confirma con la fecha completa (`dd/MM/yyyy` = 10 caracteres); las entradas
    // parciales no deben parsearse (evita interpretar «12/05/20» como el año 20).
    if (trimmed.length < 10) return;
    const parsed = parse(trimmed, DISPLAY_FORMAT, new Date());
    if (isValid(parsed)) onChange(dateToIso(parsed));
  }

  return (
    <div className={cn("relative", className)}>
      <Input
        id={id}
        value={text}
        placeholder={placeholder}
        disabled={disabled}
        inputMode="numeric"
        maxLength={10}
        aria-invalid={ariaInvalid}
        className="bg-field pr-9"
        onChange={(e) => {
          const masked = maskDate(e.target.value);
          setText(masked);
          commitText(masked);
        }}
        onBlur={() => setText(dateToDisplay(isoToDate(value)))}
      />
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          render={
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              disabled={disabled}
              aria-label="Abrir calendario"
              className="absolute top-1/2 right-1 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            />
          }
        >
          <CalendarIcon className="size-4" />
        </PopoverTrigger>
        <PopoverContent align="end" className="w-auto p-0">
          <Calendar
            mode="single"
            locale={es}
            captionLayout="dropdown"
            startMonth={startMonth}
            endMonth={endMonth}
            defaultMonth={date}
            selected={date}
            onSelect={(d: Date | undefined) => {
              onChange(dateToIso(d));
              setText(dateToDisplay(d));
              setOpen(false);
            }}
            autoFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
