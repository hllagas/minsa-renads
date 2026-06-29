"use client"

import * as React from "react"
import { ChevronLeftIcon, ChevronRightIcon } from "lucide-react"
import {
  DayButton,
  DayPicker,
  getDefaultClassNames,
  type ChevronProps,
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
      }}
      {...props}
    />
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
