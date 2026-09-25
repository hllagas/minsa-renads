"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useForm, Controller, useWatch, type Control } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";

import type { FieldConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { getResourceItem, searchResource } from "@/lib/api/lookup";
import {
  docCodigoById,
  docLengthByCodigo,
  validateDocNumber,
} from "@/lib/validation/doc-number";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { MultiEntityCombobox } from "@/components/form/multi-entity-combobox";
import { generarPassword } from "@/lib/usuarios/password";
import { Eye, EyeOff, RefreshCw } from "lucide-react";
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

/** ¿El campo ocupa las 2 columnas del formulario? `custom`/`multiselect`/`separator` y textos largos sí. */
function isFullWidth(field: FieldConfig): boolean {
  if (field.fullWidth) return true;
  if (field.type === "custom" || field.type === "multiselect" || field.type === "separator")
    return true;
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
  isCreate,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
  isCreate: boolean;
}) {
  if (field.type === "separator")
    return (
      <div className="flex items-center gap-3 pt-2">
        <span className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          {field.label}
        </span>
        <div className="flex-1 border-t" />
      </div>
    );
  if (field.type === "custom") return <>{field.render?.(control)}</>;
  if (field.type === "select") return <SelectFieldRow field={field} control={control} />;
  if (field.type === "multiselect")
    return <MultiSelectFieldRow field={field} control={control} />;
  if (field.type === "boolean")
    return <BooleanFieldRow field={field} control={control} />;
  return <InputFieldRow field={field} control={control} isCreate={isCreate} />;
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
    // Separadores visuales y campos virtuales: solo UI, no se envían al backend.
    if (f.type === "separator") continue;
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
  formClassName,
}: {
  fields: FieldConfig[];
  initial: FormValues | null;
  submitting?: boolean;
  onSubmit: (payload: FormValues) => void;
  onCancel: () => void;
  formClassName?: string;
}) {
  // `initial === null` ⇒ modo alta; con valores iniciales ⇒ edición. Lo usan los campos
  // `password` con `autogenerate` para prellenar solo al crear.
  const isCreate = initial === null;

  const { control, handleSubmit } = useForm<FormValues>({
    defaultValues: Object.fromEntries(
      fields.filter((f) => f.type !== "separator").map((f) => [f.name, defaultFor(f, initial)]),
    ),
  });

  return (
    <form
      onSubmit={handleSubmit((values) => onSubmit(buildPayload(fields, values)))}
      // `autoComplete="off"`: los formularios de administración gestionan datos de OTRAS
      // entidades/usuarios, no las credenciales del propio admin. Evita que el navegador
      // autocomplete campos o proponga guardar/actualizar contraseñas ajenas.
      autoComplete="off"
      className={formClassName ?? "grid max-h-[75vh] grid-cols-1 gap-x-5 gap-y-4 overflow-x-hidden overflow-y-auto px-2 py-2 sm:grid-cols-2"}
    >
      {fields.map((field) => (
        <ConditionalFieldWrapper key={field.name} field={field} control={control} isCreate={isCreate} />
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
  isCreate,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
  isCreate: boolean;
}) {
  const watchedValues = useWatch({ control, disabled: !field.showWhen }) as FormValues;
  const visible = field.showWhen ? field.showWhen(watchedValues ?? {}) : true;
  if (!visible) return null;
  return (
    <div className={isFullWidth(field) ? "sm:col-span-2" : undefined}>
      <FieldRow field={field} control={control} isCreate={isCreate} />
    </div>
  );
}

function InputFieldRow({
  field,
  control,
  isCreate,
}: {
  field: FieldConfig;
  control: Control<FormValues>;
  isCreate: boolean;
}) {
  const [showPassword, setShowPassword] = useState(false);

  // Asterisco visual: por `required` (validación dura) o por `requiredMark` (solo indicador).
  const showAsterisk = field.required === true || field.requiredMark === true;

  // Password autogenerado (solo en alta): prellena una contraseña segura al montar. En edición no
  // aplica (el campo password no existe en `editFields`).
  const autogen = field.type === "password" && field.autogenerate === true && isCreate;

  const inputType =
    field.type === "number"
      ? "number"
      : field.type === "date"
        ? "date"
        : field.type === "email"
          ? "email"
          : field.type === "password"
            ? showPassword ? "text" : "password"
            : "text";
  // Texto en MAYÚSCULAS por defecto; se excluye con `uppercase: false` (p. ej. `username`).
  const toUpper = field.type === "text" && field.uppercase !== false;

  // Número de documento con longitud dependiente del tipo (DNI → 8, otro → 9). Se observa el select
  // del tipo y se resuelve su `codigo` desde `identity-document-types`. Sin `docNumberFor` no observa
  // ni consulta nada (comportamiento idéntico al previo).
  const docGovId = useWatch({
    control,
    name: field.docNumberFor ?? "__none__",
    disabled: !field.docNumberFor,
  }) as number | string | null | undefined;
  const docTypesQuery = useQuery({
    queryKey: ["identity-document-types", "doc-length"],
    queryFn: () => searchResource("identity-document-types"),
    enabled: !!field.docNumberFor,
    staleTime: 30 * 60_000,
  });
  const docCodigo = field.docNumberFor ? docCodigoById(docTypesQuery.data, docGovId) : null;
  const docMaxLen = field.docNumberFor ? docLengthByCodigo(docCodigo) : undefined;

  // Validación numérica (min / max / decimals). Solo activa para type:"number" con restricciones.
  const hasNumConstraints =
    field.type === "number" &&
    (field.min != null || field.max != null || field.decimals != null);
  const validateNum = hasNumConstraints
    ? (v: unknown) => {
        const s = String(v ?? "").trim().replace(",", ".");
        if (s === "") return true;
        const n = Number(s);
        if (isNaN(n)) return "Debe ser un número válido.";
        if (field.min != null && n < field.min) return `Mínimo ${field.min}.`;
        if (field.max != null && n > field.max) return `Máximo ${field.max}.`;
        if (field.decimals != null) {
          const dec = s.split(".")[1] ?? "";
          if (dec.length > field.decimals)
            return `Máximo ${field.decimals} decimal${field.decimals !== 1 ? "es" : ""}.`;
        }
        return true;
      }
    : undefined;

  // Validación de formato de correo electrónico (solo para type:"email").
  const validateEmail =
    field.type === "email"
      ? (v: unknown) => {
          const s = String(v ?? "").trim();
          if (s === "") return true;
          return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s) || "Formato de correo inválido.";
        }
      : undefined;

  return (
    <Controller
      control={control}
      name={field.name}
      rules={{
        required: field.required ? "Campo obligatorio." : false,
        ...(field.docNumberFor
          ? { validate: (v: unknown) => validateDocNumber(v, docCodigo) }
          : validateNum
            ? { validate: validateNum }
            : validateEmail
              ? { validate: validateEmail }
              : {}),
      }}
      render={({ field: f, fieldState }) => (
        <div className="grid gap-1.5">
          <Label htmlFor={`f-${field.name}`}>
            {field.label}
            {showAsterisk ? " *" : ""}
          </Label>
          {field.type === "date" ? (
            <DatePicker
              id={`f-${field.name}`}
              value={(f.value as string | null) ?? ""}
              onChange={(iso) => f.onChange(iso)}
              ariaInvalid={!!fieldState.error}
            />
          ) : field.type === "password" ? (
            <div className="flex gap-2">
              <div className="relative flex-1">
                {autogen ? (
                  <AutogenPasswordPrefill
                    value={f.value as string | null}
                    onChange={f.onChange}
                  />
                ) : null}
                {/*
                  Campo de contraseña de ADMIN (autogenerado): el `type` es SIEMPRE `text` —
                  nunca `password` — y el enmascarado se hace por CSS (`-webkit-text-security`).
                  Así el navegador NO lo clasifica como credencial y NO ofrece «guardar/actualizar
                  contraseña» (el gestor de Chrome guardaría credenciales de OTROS usuarios en el
                  navegador del admin). El botón del ojo alterna el enmascarado, no el `type`.
                */}
                <Input
                  id={`f-${field.name}`}
                  type="text"
                  disabled={field.disabled}
                  autoComplete="off"
                  data-form-type="other"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  data-bwignore="true"
                  style={{ WebkitTextSecurity: showPassword ? "none" : "disc" } as CSSProperties}
                  value={(f.value as string | null) ?? ""}
                  onChange={(e) => f.onChange(e.target.value)}
                  onBlur={f.onBlur}
                  aria-invalid={!!fieldState.error}
                  className="pr-10"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-muted-foreground hover:text-foreground focus:outline-none"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {autogen ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => f.onChange(generarPassword())}
                  className="shrink-0"
                >
                  <RefreshCw className="mr-1.5 h-4 w-4" />
                  Regenerar
                </Button>
              ) : null}
            </div>
          ) : (
            <Input
              id={`f-${field.name}`}
              // `type="number"` activa heurísticas de pago en Chrome (muestra aviso en HTTP).
              // Usar `type="text"` + `inputMode` evita la clasificación sin perder UX numérica.
              // Prefijo «f-» en el id: rompe el match de id="numero_orden" con heurísticas de pago.
              type={inputType === "number" ? "text" : inputType}
              inputMode={
                field.numericOnly || field.docNumberFor
                  ? "numeric"
                  : inputType === "number"
                    ? "decimal"
                    : undefined
              }
              maxLength={docMaxLen}
              disabled={field.disabled}
              autoComplete="off"
              data-form-type="other"
              data-lpignore="true"
              value={(f.value as string | number | null) ?? ""}
              onChange={(e) => {
                let val = e.target.value;
                // Documento: solo dígitos, recortado a la longitud del tipo (DNI 8 / otro 9).
                if (field.docNumberFor)
                  val = val.replace(/\D/g, "").slice(0, docMaxLen);
                // Numérico estricto: solo dígitos (teléfono, código numérico).
                else if (field.numericOnly)
                  val = val.replace(/\D/g, "");
                else if (toUpper) val = val.toUpperCase();
                f.onChange(val);
              }}
              onBlur={f.onBlur}
              aria-invalid={!!fieldState.error}
              className={toUpper ? "uppercase" : undefined}
            />
          )}
          {field.helperText ? (
            <p className="text-xs text-muted-foreground">{field.helperText}</p>
          ) : null}
          {fieldState.error ? (
            <p className="text-sm text-destructive">{fieldState.error.message}</p>
          ) : null}
        </div>
      )}
    />
  );
}

/**
 * Prellena una contraseña autogenerada al montar el campo (solo en alta). No renderiza nada; usa un
 * efecto para escribir el valor inicial una sola vez sin sobrescribir ediciones manuales posteriores.
 */
function AutogenPasswordPrefill({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (v: string) => void;
}) {
  const done = useRef(false);
  useEffect(() => {
    if (done.current) return;
    done.current = true;
    if (!value) onChange(generarPassword());
    // Solo al montar; `onChange` es estable por render del Controller.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
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
            {field.required || field.requiredMark ? " *" : ""}
          </Label>
          <MultiEntityCombobox
            endpoint={field.optionsEndpoint!}
            params={field.optionsParams}
            toLabel={field.optionsToLabel}
            value={Array.isArray(f.value) ? (f.value as number[]) : []}
            onChange={(val) => f.onChange(val)}
          />
          {field.helperText ? (
            <p className="text-xs text-muted-foreground">{field.helperText}</p>
          ) : null}
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

  // Cascada por **entidad relacionada** (async): observa el id del campo padre, pide su detalle y
  // mapea a params. Deshabilita el select hasta resolver. Sin `optionsParamsFromEntity` no observa ni
  // consulta nada (comportamiento idéntico al previo).
  const entityDep = field.optionsParamsFromEntity;
  const depId = useWatch({
    control,
    name: entityDep?.field ?? "__none__",
    disabled: !entityDep,
  }) as string | number | null | undefined;
  const depQuery = useQuery({
    queryKey: [entityDep?.endpoint, "params-src", depId],
    queryFn: () => getResourceItem(entityDep!.endpoint, depId as string | number),
    enabled: !!entityDep && depId != null && depId !== "",
    staleTime: 60_000,
  });
  const entityParams = entityDep && depQuery.data ? entityDep.toParams(depQuery.data) : undefined;
  // El select por entidad no puede filtrar hasta tener params → se deshabilita mientras tanto.
  const entityGated = !!entityDep && !entityParams;

  // Params dinámicos: prioridad `optionsParamsFrom` > `optionsParamsFromEntity` (async) > estático.
  const dynamicParams = field.optionsParamsFrom
    ? field.optionsParamsFrom(watchedValues ?? {})
    : entityDep
      ? entityParams
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
            {field.required || field.requiredMark ? " *" : ""}
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
          ) : field.optionsValueKey && field.optionsSearchable ? (
            // FK de PK textual con búsqueda server-side (catálogos grandes: UE, ipress).
            <EntityCombobox
              endpoint={field.optionsEndpoint!}
              params={dynamicParams}
              valueKey={field.optionsValueKey}
              toLabel={field.optionsToLabel}
              value={(f.value as string | null) ?? null}
              onChange={(val) => f.onChange(val)}
              disabled={field.disabled || entityGated}
              placeholder={entityGated ? "Elige primero el campo relacionado…" : undefined}
            />
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
              disabled={field.disabled || entityGated}
              placeholder={entityGated ? "Elige primero el campo relacionado…" : undefined}
            />
          )}
          {field.helperText ? (
            <p className="text-xs text-muted-foreground">{field.helperText}</p>
          ) : null}
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
