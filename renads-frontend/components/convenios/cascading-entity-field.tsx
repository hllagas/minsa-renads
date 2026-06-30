"use client";

import { useState } from "react";
import { useController, type Control } from "react-hook-form";

import type { FormValues } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { EntityCombobox } from "@/components/form/entity-combobox";

/**
 * Par de selects en cascada: un **tipo** (catálogo) filtra la lista de **entidades** concretas.
 * Solo se persiste la entidad (`name`); el tipo es UX (no se almacena: se deriva de la entidad).
 * Se usa para órgano regional (tipo → `regional-organs`) y universidad (tipo → `universities`).
 */
export function CascadingEntityField({
  control,
  name,
  typeLabel,
  typeEndpoint,
  entityLabel,
  entityEndpoint,
  filterParam,
  required,
  toLabel,
}: {
  control: Control<FormValues>;
  /** Campo del formulario donde se guarda el id de la entidad seleccionada. */
  name: string;
  typeLabel: string;
  typeEndpoint: string;
  entityLabel: string;
  entityEndpoint: string;
  /** Query param del endpoint de entidades que filtra por el tipo elegido. */
  filterParam: string;
  required?: boolean;
  toLabel?: (row: WithId) => string;
}) {
  const [tipoId, setTipoId] = useState<number | null>(null);

  const entidad = useController({
    control,
    name,
    defaultValue: null,
    rules: required
      ? { validate: (v) => (v != null && v !== "") || "Campo obligatorio." }
      : undefined,
  });

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div className="grid gap-1.5">
        <Label>
          {typeLabel}
          {required ? " *" : ""}
        </Label>
        <EntityCombobox
          endpoint={typeEndpoint}
          value={tipoId}
          onChange={(v) => {
            setTipoId(v);
            entidad.field.onChange(null); // la entidad depende del tipo
          }}
          placeholder="Seleccionar tipo…"
        />
      </div>

      <div className="grid gap-1.5">
        <Label>
          {entityLabel}
          {required ? " *" : ""}
        </Label>
        {tipoId != null ? (
          // `key` remonta el combobox al cambiar el tipo (reinicia búsqueda interna).
          <EntityCombobox
            key={tipoId}
            endpoint={entityEndpoint}
            params={{ [filterParam]: String(tipoId) }}
            toLabel={toLabel}
            value={entidad.field.value as number | null}
            onChange={(v) => entidad.field.onChange(v)}
            placeholder={`Buscar ${entityLabel.toLowerCase()}…`}
          />
        ) : (
          <Input disabled placeholder="Elige primero el tipo…" />
        )}
        {entidad.fieldState.error ? (
          <p className="text-sm text-destructive">{entidad.fieldState.error.message}</p>
        ) : null}
      </div>
    </div>
  );
}
