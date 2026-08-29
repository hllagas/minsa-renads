"use client";

import { useEffect, useRef } from "react";
import { useForm, Controller, useWatch, type Control } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";

import type { FieldConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { searchResource } from "@/lib/api/lookup";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { MultiEntityCombobox } from "@/components/form/multi-entity-combobox";
import { DatePicker } from "@/components/form/date-picker";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type FormValues = Record<string, unknown>;

/** Campos de texto cuyo contenido suele ser largo → ocupan todo el ancho aunque no se marquen. */
const AUTO_FULL_WIDTH_NAMES =
  /^(nombre|denominacion|descripcion|direccion|observacion|observaciones|justificacion|motivo)/;

/** ¿El campo ocupa las 2 columnas del formulario? `custom`/`multiselect` y textos largos sí. */
function isFullWidth(field: FieldConfig): boolean {
  if (field.fullWidth) return true;
  if (field.type === "custom" || field.type === "multiselect") return true;
  if (
    (field.type === "text" || field.type === "email") &&
    AUTO_FULL_WIDTH_NAMES.test(field.name)
  )
    return true;
  return false;
}

/** Selecciona el control adecuado para un campo (sin envoltorio de columna). */
function FieldRow({
  field,
  control,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
}) {
  if (field.type === "custom") return <>{field.render?.(control)}</>;
  if (field.type === "select") return <SelectFieldRow field={field} control={control} />;
  if (field.type === "multiselect")
    return <MultiSelectFieldRow field={field} control={control} />;
  if (field.type === "boolean")
    return <BooleanFieldRow field={field} control={control} />;
  return <InputFieldRow field={field} control={control} />;
}

function defaultFor(field: FieldConfig, initial: FormValues | null): unknown {
  if (field.type === "multiselect") {
    const v = initial?.[field.name];
    return Array.isArray(v) ? v : [];
  }
  const v = initial?.[field.name];
  if (v !== undefined && v !== null) return v;
  if (field.defaultValue !== undefined) return field.defaultValue;
  if (field.type === "boolean") return false;
  if (field.type === "number" || field.type === "select" || field.type === "custom")
    return null;
  return "";
}

/** Construye el payload para el backend, omitiendo opcionales vacíos. */
function buildPayload(fields: FieldConfig[], values: FormValues): FormValues {
  const out: FormValues = {};
  for (const f of fields) {
    // Campos virtuales: solo UI (p. ej. filtro de cascada). No se envían al backend.
    if (f.virtual) continue;
    // Campos ocultos por `showWhen`: se excluyen del payload.
    if (f.showWhen && !f.showWhen(values)) continue;
    const v = values[f.name];
    if (f.type === "boolean") {
      out[f.name] = Boolean(v);
      continue;
    }
    if (f.type === "multiselect") {
      // Siempre se envía el array (incluido `[]` para vaciar la relación).
      out[f.name] = (Array.isArray(v) ? v : []).map(Number);
      continue;
    }
    if (f.type === "password") {
      // Contraseña write-only: solo se incluye si hay valor; nunca se imprime ni se cachea.
      if (typeof v === "string" && v !== "") out[f.name] = v;
      continue;
    }
    if (f.type === "custom") {
      // Un control compuesto puede aportar varias claves (p. ej. tipo + id de entidad).
      for (const key of f.payloadKeys ?? [f.name]) {
        const kv = values[key];
        const vacioKey = kv === "" || kv === null || kv === undefined;
        if (vacioKey) {
          if (f.required) out[key] = kv;
          continue;
        }
        out[key] = Number(kv);
      }
      continue;
    }
    const vacio = v === "" || v === null || v === undefined;
    if (vacio) {
      if (f.required) out[f.name] = v; // deja que el backend valide el requerido
      continue;
    }
    out[f.name] = f.type === "number" ? Number(v) : v;
  }
  return out;
}

export function ResourceForm({
  fields,
  initial,
  submitting,
  onSubmit,
  onCancel,
}: {
  fields: FieldConfig[];
  initial: FormValues | null;
  submitting?: boolean;
  onSubmit: (payload: FormValues) => void;
  onCancel: () => void;
}) {
  const { control, handleSubmit } = useForm<FormValues>({
    defaultValues: Object.fromEntries(
      fields.map((f) => [f.name, defaultFor(f, initial)]),
    ),
  });

  return (
    <form
      onSubmit={handleSubmit((values) => onSubmit(buildPayload(fields, values)))}
      className="grid max-h-[75vh] grid-cols-1 gap-x-5 gap-y-4 overflow-x-hidden overflow-y-auto px-2 py-2 sm:grid-cols-2"
    >
      {fields.map((field) => (
        <ConditionalFieldWrapper key={field.name} field={field} control={control} />
      ))}
      <div className="flex justify-end gap-2 pt-2 sm:col-span-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Guardando…" : "Guardar"}
        </Button>
      </div>
    </form>
  );
}

/** Envuelve un campo con visibilidad condicional (`showWhen`). Sin condición = siempre visible. */
function ConditionalFieldWrapper({
  field,
  control,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
}) {
  const watchedValues = useWatch({ control, disabled: !field.showWhen }) as FormValues;
  const visible = field.showWhen ? field.showWhen(watchedValues ?? {}) : true;
  if (!visible) return null;
  return (
    <div className={isFullWidth(field) ? "sm:col-span-2" : undefined}>
      <FieldRow field={field} control={control} />
    </div>
  );
}

function InputFieldRow({
  field,
  control,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
}) {
  const inputType =
    field.type === "number"
      ? "number"
      : field.type === "date"
        ? "date"
        : field.type === "email"
          ? "email"
          : field.type === "password"
            ? "password"
            : "text";
  // Texto en MAYÚSCULAS por defecto; se excluye con `uppercase: false` (p. ej. `username`).
  const toUpper = field.type === "text" && field.uppercase !== false;
  return (
    <Controller
      control={control}
      name={field.name}
      rules={{ required: field.required ? "Campo obligatorio." : false }}
      render={({ field: f, fieldState }) => (
        <div className="grid gap-1.5">
          <Label htmlFor={`f-${field.name}`}>
            {field.label}
            {field.required ? " *" : ""}
          </Label>
          {field.type === "date" ? (
            <DatePicker
              id={`f-${field.name}`}
              value={(f.value as string | null) ?? ""}
              onChange={(iso) => f.onChange(iso)}
              ariaInvalid={!!fieldState.error}
            />
          ) : (
            <Input
              id={`f-${field.name}`}
              // `type="number"` activa heurísticas de pago en Chrome (muestra aviso en HTTP).
              // Usar `type="text"` + `inputMode` evita la clasificación sin perder UX numérica.
              // Prefijo «f-» en el id: rompe el match de id="numero_orden" con heurísticas de pago.
              type={inputType === "number" ? "text" : inputType}
              inputMode={inputType === "number" ? "decimal" : undefined}
              disabled={field.disabled}
              autoComplete={field.type === "password" ? "new-password" : "off"}
              // Excluye el campo del pipeline de detección de pago de Chrome/gestores de contraseñas.
              data-form-type="other"
              data-lpignore="true"
              value={(f.value as string | number | null) ?? ""}
              onChange={(e) =>
                f.onChange(toUpper ? e.target.value.toUpperCase() : e.target.value)
              }
              onBlur={f.onBlur}
              aria-invalid={!!fieldState.error}
              className={toUpper ? "uppercase" : undefined}
            />
          )}
          {fieldState.error ? (
            <p className="text-sm text-destructive">{fieldState.error.message}</p>
          ) : null}
        </div>
      )}
    />
  );
}

function MultiSelectFieldRow({
  field,
  control,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
}) {
  return (
    <Controller
      control={control}
      name={field.name}
      rules={{
        validate: (v) =>
          !field.required || (Array.isArray(v) && v.length > 0)
            ? true
            : "Selecciona al menos una opción.",
      }}
      render={({ field: f, fieldState }) => (
        <div className="grid gap-1.5">
          <Label>
            {field.label}
            {field.required ? " *" : ""}
          </Label>
          <MultiEntityCombobox
            endpoint={field.optionsEndpoint!}
            params={field.optionsParams}
            toLabel={field.optionsToLabel}
            value={Array.isArray(f.value) ? (f.value as number[]) : []}
            onChange={(val) => f.onChange(val)}
          />
          {fieldState.error ? (
            <p className="text-sm text-destructive">{fieldState.error.message}</p>
          ) : null}
        </div>
      )}
    />
  );
}

function BooleanFieldRow({
  field,
  control,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
}) {
  return (
    <Controller
      control={control}
      name={field.name}
      render={({ field: f }) => (
        <div className="flex items-center justify-between gap-2">
          <Label htmlFor={`f-${field.name}`}>{field.label}</Label>
          <Switch
            id={`f-${field.name}`}
            checked={Boolean(f.value)}
            onCheckedChange={(checked) => f.onChange(checked)}
          />
        </div>
      )}
    />
  );
}

function SelectFieldRow({
  field,
  control,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
}) {
  // Valores en vivo del formulario, solo si el campo depende de otros (cascada). Sin
  // `optionsParamsFrom`/`resetsOn` no se observa nada y el comportamiento es idéntico al previo.
  const watchesValues = !!field.optionsParamsFrom;
  const watchedValues = useWatch({ control, disabled: !watchesValues }) as FormValues;
  // Params dinámicos: prioridad de `optionsParamsFrom` sobre `optionsParams` estático.
  const dynamicParams = field.optionsParamsFrom
    ? field.optionsParamsFrom(watchedValues ?? {})
    : field.optionsParams;

  return (
    <Controller
      control={control}
      name={field.name}
      rules={{
        validate: (v) =>
          !field.required || (v !== null && v !== undefined && v !== "")
            ? true
            : "Campo obligatorio.",
      }}
      render={({ field: f, fieldState }) => (
        <div className="grid gap-1.5">
          <Label>
            {field.label}
            {field.required ? " *" : ""}
          </Label>
          {field.resetsOn?.length ? (
            <ResetOnParentChange
              control={control}
              parents={field.resetsOn}
              onReset={() => f.onChange(null)}
            />
          ) : null}
          {field.choices ? (
            <Select
              items={field.choices.map((c) => ({ value: c.value, label: c.label }))}
              value={(f.value as string | null) ?? null}
              onValueChange={(v: string | null) => f.onChange(v)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar…" />
              </SelectTrigger>
              <SelectContent>
                {field.choices.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : field.optionsValueKey ? (
            <CodeSelect
              endpoint={field.optionsEndpoint!}
              params={dynamicParams}
              valueKey={field.optionsValueKey}
              toLabel={field.optionsToLabel}
              value={(f.value as string | null) ?? null}
              onChange={(v) => f.onChange(v)}
            />
          ) : (
            <EntityCombobox
              endpoint={field.optionsEndpoint!}
              params={dynamicParams}
              toLabel={field.optionsToLabel}
              value={f.value as number | null}
              onChange={(val) => f.onChange(val)}
            />
          )}
          {fieldState.error ? (
            <p className="text-sm text-destructive">{fieldState.error.message}</p>
          ) : null}
        </div>
      )}
    />
  );
}

/**
 * Resetea un campo dependiente cuando **cambia** (tras el montaje) alguno de sus campos padre.
 * No dispara en el primer render, para no borrar un valor precargado en edición; solo reacciona a
 * cambios reales del padre, evitando bucles.
 */
function ResetOnParentChange({
  control,
  parents,
  onReset,
}: {
  control: Control<FormValues>;
  parents: string[];
  onReset: () => void;
}) {
  const parentValues = useWatch({ control, name: parents }) as unknown[];
  const previous = useRef<unknown[] | null>(null);

  useEffect(() => {
    if (previous.current === null) {
      // Primer render: fija la línea base sin resetear (respeta valores precargados en edición).
      previous.current = parentValues;
      return;
    }
    const changed = parentValues.some((v, i) => v !== previous.current![i]);
    previous.current = parentValues;
    if (changed) onReset();
    // `onReset` es estable por render del Controller; se omite para evitar re-ejecuciones.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parentValues]);

  return null;
}

/**
 * Select por **código**: opciones traídas de un endpoint, pero el valor enviado es una clave de
 * cadena (`valueKey`, p. ej. `codigo`) en vez del id. Muestra `toLabel`/`nombre` como descripción.
 */
function CodeSelect({
  endpoint,
  params,
  valueKey,
  toLabel,
  value,
  onChange,
}: {
  endpoint: string;
  params?: Record<string, string>;
  valueKey: string;
  toLabel?: (row: WithId) => string;
  value: string | null;
  onChange: (value: string | null) => void;
}) {
  const query = useQuery({
    queryKey: [endpoint, "code-select", params ?? null],
    queryFn: () => searchResource(endpoint, { params }),
    staleTime: 60_000,
  });
  const items = (query.data ?? [])
    .map((row) => ({
      value: String(row[valueKey] ?? ""),
      label: toLabel ? toLabel(row) : String(row.nombre ?? row[valueKey] ?? row.id),
    }))
    .filter((i) => i.value !== "");

  return (
    <Select
      items={items}
      value={value}
      onValueChange={(v: string | null) => onChange(v)}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Seleccionar…" />
      </SelectTrigger>
      <SelectContent>
        {items.map((i) => (
          <SelectItem key={i.value} value={i.value}>
            {i.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
