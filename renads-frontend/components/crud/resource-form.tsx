"use client";

import { useForm, Controller, type Control } from "react-hook-form";

import type { FieldConfig } from "@/lib/crud/types";
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

function defaultFor(field: FieldConfig, initial: FormValues | null): unknown {
  if (field.type === "multiselect") {
    const v = initial?.[field.name];
    return Array.isArray(v) ? v : [];
  }
  const v = initial?.[field.name];
  if (v !== undefined && v !== null) return v;
  if (field.defaultValue !== undefined) return field.defaultValue;
  if (field.type === "boolean") return false;
  if (field.type === "number" || field.type === "select") return null;
  return "";
}

/** Construye el payload para el backend, omitiendo opcionales vacíos. */
function buildPayload(fields: FieldConfig[], values: FormValues): FormValues {
  const out: FormValues = {};
  for (const f of fields) {
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
      className="grid max-h-[60vh] gap-4 overflow-y-auto px-1"
    >
      {fields.map((field) =>
        field.type === "select" ? (
          <SelectFieldRow key={field.name} field={field} control={control} />
        ) : field.type === "multiselect" ? (
          <MultiSelectFieldRow key={field.name} field={field} control={control} />
        ) : field.type === "boolean" ? (
          <BooleanFieldRow key={field.name} field={field} control={control} />
        ) : (
          <InputFieldRow key={field.name} field={field} control={control} />
        ),
      )}
      <div className="flex justify-end gap-2 pt-2">
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
          <Label htmlFor={field.name}>
            {field.label}
            {field.required ? " *" : ""}
          </Label>
          {field.type === "date" ? (
            <DatePicker
              id={field.name}
              value={(f.value as string | null) ?? ""}
              onChange={(iso) => f.onChange(iso)}
              ariaInvalid={!!fieldState.error}
            />
          ) : (
            <Input
              id={field.name}
              type={inputType}
              autoComplete={field.type === "password" ? "new-password" : undefined}
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
          <Label htmlFor={field.name}>{field.label}</Label>
          <Switch
            id={field.name}
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
          ) : (
            <EntityCombobox
              endpoint={field.optionsEndpoint!}
              params={field.optionsParams}
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
