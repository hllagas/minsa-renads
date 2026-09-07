"use client"

import * as React from "react"
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import {
  DayButton,
  DayPicker,
  getDefaultClassNames,
  type ChevronProps,
  type DropdownProps,
} from "react-day-picker"

import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"

/**
 * Calendario shadcn sobre `react-day-picker` (v10). Estilado con Tailwind v4 y los tokens del
 * proyecto (claro/oscuro vía variables CSS). Pensado para usarse en modo `single` o `range`.
 */
function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: React.ComponentProps<typeof DayPicker>) {
  const defaultClassNames = getDefaultClassNames()

  return (
    <DayPicker
      data-slot="calendar"
      showOutsideDays={showOutsideDays}
      className={cn("w-fit p-3", className)}
      classNames={{
        root: cn("relative", defaultClassNames.root),
        months: cn(
          "flex flex-col gap-4 sm:flex-row",
          defaultClassNames.months,
        ),
        month: cn("flex flex-col gap-4", defaultClassNames.month),
        nav: cn(
          "absolute inset-x-0 top-0 flex items-center justify-between",
          defaultClassNames.nav,
        ),
        button_previous: cn(
          buttonVariants({ variant: "ghost", size: "icon-sm" }),
          "text-muted-foreground hover:text-foreground",
          defaultClassNames.button_previous,
        ),
        button_next: cn(
          buttonVariants({ variant: "ghost", size: "icon-sm" }),
          "text-muted-foreground hover:text-foreground",
          defaultClassNames.button_next,
        ),
        month_caption: cn(
          "flex h-7 items-center justify-center px-8 text-sm font-medium capitalize",
          defaultClassNames.month_caption,
        ),
        caption_label: cn("select-none", defaultClassNames.caption_label),
        // Navegación por desplegables de mes/año (captionLayout="dropdown").
        dropdowns: cn(
          "flex items-center justify-center gap-1.5 text-sm font-medium",
          defaultClassNames.dropdowns,
        ),
        dropdown_root: cn("relative", defaultClassNames.dropdown_root),
        dropdown: cn(
          buttonVariants({ variant: "outline", size: "sm" }),
          "h-7 rounded-md px-2 capitalize",
          // Colores explícitos del <select> y de sus <option> para que la lista desplegable
          // nativa sea legible (evita texto claro sobre fondo claro en modo oscuro).
          "bg-popover text-popover-foreground",
          "[&>option]:bg-popover [&>option]:text-popover-foreground",
          defaultClassNames.dropdown,
        ),
        month_grid: cn("w-full border-collapse", defaultClassNames.month_grid),
        weekdays: cn("flex", defaultClassNames.weekdays),
        weekday: cn(
          "w-8 flex-1 select-none text-[0.8rem] font-normal text-muted-foreground",
          defaultClassNames.weekday,
        ),
        week: cn("mt-2 flex w-full", defaultClassNames.week),
        day: cn(
          // Estilos del rango: extremos redondeados, intermedio con fondo de acento.
          "group/day relative size-8 flex-1 select-none p-0 text-center text-sm",
          "[&:has([aria-selected])]:bg-accent",
          "[&:first-child[data-selected=true]_button]:rounded-l-md",
          "[&:last-child[data-selected=true]_button]:rounded-r-md",
          "data-[range-middle=true]:rounded-none data-[range-middle=true]:bg-accent",
          "data-[range-start=true]:rounded-l-md data-[range-start=true]:bg-accent",
          "data-[range-end=true]:rounded-r-md data-[range-end=true]:bg-accent",
          defaultClassNames.day,
        ),
        range_start: cn(defaultClassNames.range_start),
        range_middle: cn(defaultClassNames.range_middle),
        range_end: cn(defaultClassNames.range_end),
        today: cn(
          "[&:not([data-selected=true])>button]:bg-accent/50 rounded-md",
          defaultClassNames.today,
        ),
        outside: cn(
          "text-muted-foreground aria-selected:text-muted-foreground",
          defaultClassNames.outside,
        ),
        disabled: cn("text-muted-foreground opacity-50", defaultClassNames.disabled),
        hidden: cn("invisible", defaultClassNames.hidden),
        ...classNames,
      }}
      components={{
        Chevron: CalendarChevron,
        DayButton: CalendarDayButton,
        Dropdown: CalendarDropdown,
      }}
      {...props}
    />
  )
}

/**
 * Desplegable de mes/año (captionLayout="dropdown"). Reemplaza al `Dropdown` por defecto de
 * react-day-picker, que renderiza un `<select>` MÁS un `<span>` con la etiqueta visible: al
 * estilar el `<select>` como pill se veían ambos (pill + texto duplicado, desalineados). Aquí
 * se renderiza solo el `<select>` nativo estilado, sin el span duplicado.
 */
function CalendarDropdown({
  options,
  value,
  onChange,
  className,
  ...props
}: DropdownProps) {
  // El desplegable de año lista valores >= 1000: se ordena descendente (año más reciente
  // primero). El de mes (valores 0–11) conserva el orden natural.
  const isYear = (options?.[0]?.value ?? 0) >= 1000
  const items = isYear ? [...(options ?? [])].reverse() : options ?? []

  return (
    <select
      // rdp v10 no propaga `classNames.dropdown` al componente custom, así que el estilo del
      // pill se aplica aquí explícitamente (borde, alto y colores legibles en claro/oscuro).
      className={cn(
        buttonVariants({ variant: "outline", size: "sm" }),
        "h-7 w-fit rounded-md px-2 font-medium capitalize",
        "bg-popover text-popover-foreground",
        "[&>option]:bg-popover [&>option]:text-popover-foreground",
        className,
      )}
      value={value}
      onChange={onChange}
      {...props}
    >
      {items.map((opt) => (
        <option key={opt.value} value={opt.value} disabled={opt.disabled}>
          {opt.label}
        </option>
      ))}
    </select>
  )
}

/** Iconos de navegación entre meses (izquierda/derecha) con lucide. */
function CalendarChevron({ orientation, className, ...props }: ChevronProps) {
  if (orientation === "left") {
    return <ChevronLeftIcon className={cn("size-4", className)} {...props} />
  }
  return <ChevronRightIcon className={cn("size-4", className)} {...props} />
}

/** Botón de día con foco automático y estilos de selección (extremos del rango). */
function CalendarDayButton({
  className,
  day,
  modifiers,
  ...props
}: React.ComponentProps<typeof DayButton>) {
  const ref = React.useRef<HTMLButtonElement>(null)
  React.useEffect(() => {
    if (modifiers.focused) ref.current?.focus()
  }, [modifiers.focused])

  return (
    <button
      ref={ref}
      data-day={day.date.toLocaleDateString()}
      data-selected={modifiers.selected}
      data-range-start={modifiers.range_start}
      data-range-end={modifiers.range_end}
      data-range-middle={modifiers.range_middle}
      className={cn(
        buttonVariants({ variant: "ghost", size: "icon-sm" }),
        "size-8 rounded-md font-normal",
        "data-[selected=true]:bg-primary data-[selected=true]:text-primary-foreground data-[selected=true]:hover:bg-primary/90",
        "data-[range-middle=true]:bg-transparent data-[range-middle=true]:text-accent-foreground data-[range-middle=true]:hover:bg-transparent",
        className,
      )}
      {...props}
    />
  )
}

export { Calendar }
