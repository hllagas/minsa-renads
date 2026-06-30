"use client";

import { useController, type Control } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";

import type { FormValues } from "@/lib/crud/types";
import {
  SOLICITANTE_ENTITIES,
  listSolicitanteTypes,
} from "@/lib/convenios/solicitante";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { EntityCombobox } from "@/components/form/entity-combobox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Selector compuesto de la entidad solicitante (relación polimórfica del convenio):
 * un primer `select` elige el **tipo** de entidad (`solicitante_tipo_contenido` = `ContentType.id`)
 * y el segundo elige la **entidad** concreta (`solicitante_id_objeto`) del endpoint correspondiente.
 * Al cambiar el tipo se reinicia la entidad seleccionada.
 */
export function SolicitanteField({ control }: { control: Control<FormValues> }) {
  const typesQuery = useQuery({
    queryKey: ["solicitante-content-types"],
    queryFn: listSolicitanteTypes,
    staleTime: 5 * 60_000,
  });

  const tipo = useController({
    control,
    name: "solicitante_tipo_contenido",
    defaultValue: null,
    rules: { validate: (v) => (v != null && v !== "") || "Campo obligatorio." },
  });
  const entidad = useController({
    control,
    name: "solicitante_id_objeto",
    defaultValue: null,
    rules: { validate: (v) => (v != null && v !== "") || "Campo obligatorio." },
  });

  const tipoId = tipo.field.value as number | null;
  const tipos = typesQuery.data ?? [];
  const modelo = tipos.find((t) => t.id === tipoId)?.model;
  const endpoint = modelo ? SOLICITANTE_ENTITIES[modelo]?.endpoint : undefined;

  const items = tipos.map((t) => ({
    value: String(t.id),
    label: SOLICITANTE_ENTITIES[t.model]?.label ?? t.model,
  }));

  return (
    <div className="grid gap-4">
      <div className="grid gap-1.5">
        <Label>Tipo de entidad solicitante *</Label>
        <Select
          items={items}
          value={tipoId != null ? String(tipoId) : null}
          onValueChange={(v: string | null) => {
            tipo.field.onChange(v ? Number(v) : null);
            entidad.field.onChange(null); // la entidad depende del tipo
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Seleccionar tipo…" />
          </SelectTrigger>
          <SelectContent>
            {items.map((i) => (
              <SelectItem key={i.value} value={i.value}>
                {i.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {tipo.fieldState.error ? (
          <p className="text-sm text-destructive">{tipo.fieldState.error.message}</p>
        ) : null}
      </div>

      <div className="grid gap-1.5">
        <Label>Entidad solicitante *</Label>
        {endpoint ? (
          // `key` remonta el combobox al cambiar el tipo (reinicia búsqueda interna).
          <EntityCombobox
            key={endpoint}
            endpoint={endpoint}
            value={entidad.field.value as number | null}
            onChange={(val) => entidad.field.onChange(val)}
            placeholder="Buscar entidad…"
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
