"use client";

import { useEffect } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";

import type { FormValues } from "@/lib/crud/types";
import { searchResource } from "@/lib/api/lookup";
import type { WithId } from "@/lib/api/query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { DatePicker } from "@/components/form/date-picker";
import { SolicitanteField } from "@/components/convenios/solicitante-field";
import { CascadingEntityField } from "@/components/convenios/cascading-entity-field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Formulario de alta de convenio con reglas de negocio Marco/Específico:
 * - `tipo_convenio` se bloquea una vez elegido (no se cambia el tipo del convenio).
 * - `convenio_marco` y `max_campos_clinicos` solo aplican a **Específico**: deshabilitados y
 *   limpiados cuando el tipo es Marco; obligatorios cuando es Específico.
 */
export function ConvenioCreateForm({
  submitting,
  onSubmit,
  onCancel,
}: {
  submitting?: boolean;
  onSubmit: (payload: FormValues) => void;
  onCancel: () => void;
}) {
  const { control, handleSubmit, setValue } = useForm<FormValues>({
    defaultValues: {
      tipo_convenio: null,
      titulo: "",
      codigo: "",
      plantilla: null,
      convenio_marco: null,
      solicitante_tipo_contenido: null,
      solicitante_id_objeto: null,
      organo_regional: null,
      universidad: null,
      fecha_solicitud: "",
      max_campos_clinicos: "",
    },
  });

  const tipoId = useWatch({ control, name: "tipo_convenio" }) as number | null;

  // Catálogo de tipos (pequeño) para saber si el seleccionado es "Específico".
  const typesQuery = useQuery({
    queryKey: ["convention-types", "all"],
    queryFn: () => searchResource("convention-types"),
    staleTime: 5 * 60_000,
  });
  const selected = typesQuery.data?.find((t) => t.id === tipoId);
  const isEspecifico =
    !!selected &&
    /espec/i.test(String(selected.nombre ?? selected.codigo ?? ""));

  // Opciones del select de tipo (catálogo pequeño → dropdown, no búsqueda).
  const tipoItems = (typesQuery.data ?? []).map((t) => ({
    value: String(t.id),
    label: String(t.nombre ?? t.codigo ?? t.id),
  }));

  // Al pasar a Marco (o sin tipo), limpiar los campos solo-Específico.
  useEffect(() => {
    if (!isEspecifico) {
      setValue("convenio_marco", null);
      setValue("max_campos_clinicos", "");
    }
  }, [isEspecifico, setValue]);

  function submit(values: FormValues) {
    const payload: FormValues = {
      tipo_convenio: Number(values.tipo_convenio),
      titulo: values.titulo,
      solicitante_tipo_contenido: Number(values.solicitante_tipo_contenido),
      solicitante_id_objeto: Number(values.solicitante_id_objeto),
      organo_regional: Number(values.organo_regional),
      universidad: Number(values.universidad),
      fecha_solicitud: values.fecha_solicitud,
    };
    if (values.codigo) payload.codigo = values.codigo;
    if (values.plantilla != null) payload.plantilla = Number(values.plantilla);
    if (isEspecifico) {
      if (values.convenio_marco != null)
        payload.convenio_marco = Number(values.convenio_marco);
      if (values.max_campos_clinicos !== "" && values.max_campos_clinicos != null)
        payload.max_campos_clinicos = Number(values.max_campos_clinicos);
    }
    onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="grid gap-4">
      {/* Tipo de convenio — se bloquea tras elegirlo */}
      <Controller
        control={control}
        name="tipo_convenio"
        rules={{ validate: (v) => (v != null && v !== "") || "Campo obligatorio." }}
        render={({ field, fieldState }) => (
          <Row label="Tipo de convenio" required error={fieldState.error?.message}>
            <Select
              items={tipoItems}
              value={field.value != null ? String(field.value) : null}
              onValueChange={(v: string | null) =>
                field.onChange(v ? Number(v) : null)
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar tipo…" />
              </SelectTrigger>
              <SelectContent>
                {tipoItems.map((i) => (
                  <SelectItem key={i.value} value={i.value}>
                    {i.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Row>
        )}
      />

      {/* Título / Código (mayúsculas) */}
      <Controller
        control={control}
        name="titulo"
        rules={{ required: "Campo obligatorio." }}
        render={({ field, fieldState }) => (
          <Row label="Título" required error={fieldState.error?.message}>
            <Input
              className="uppercase"
              value={(field.value as string) ?? ""}
              onChange={(e) => field.onChange(e.target.value.toUpperCase())}
              aria-invalid={!!fieldState.error}
            />
          </Row>
        )}
      />
      {/* Nomenclatura (antes "Código"): solo editable cuando el convenio esté en
          estado ENVIADO_VICEPAS; en el alta siempre va bloqueada. */}
      <Row label="Nomenclatura">
        <Input
          disabled
          placeholder="Se asigna en el estado ENVIADO_VICEPAS"
        />
      </Row>

      {/* Plantilla (opcional) */}
      <Controller
        control={control}
        name="plantilla"
        render={({ field }) => (
          <Row label="Plantilla">
            <EntityCombobox
              endpoint="convention-templates"
              value={field.value as number | null}
              onChange={(v) => field.onChange(v)}
              placeholder="Buscar plantilla…"
            />
          </Row>
        )}
      />

      {/* Convenio Marco — solo Específico */}
      <Controller
        control={control}
        name="convenio_marco"
        rules={{
          validate: (v) =>
            !isEspecifico || (v != null && v !== "")
              ? true
              : "Obligatorio para convenios Específicos.",
        }}
        render={({ field, fieldState }) => (
          <Row
            label="Convenio Marco (solo Específico)"
            required={isEspecifico}
            error={fieldState.error?.message}
          >
            <EntityCombobox
              endpoint="conventions"
              toLabel={(row: WithId) => String(row.titulo ?? row.codigo ?? row.id)}
              value={field.value as number | null}
              onChange={(v) => field.onChange(v)}
              disabled={!isEspecifico}
              placeholder={isEspecifico ? "Buscar…" : "Solo para Específico"}
            />
          </Row>
        )}
      />

      {/* Entidad solicitante (control compuesto) */}
      <SolicitanteField control={control} />

      {/* Órgano regional (tipo → entidad en cascada) */}
      <CascadingEntityField
        control={control}
        name="organo_regional"
        typeLabel="Tipo de órgano regional"
        typeEndpoint="regional-organ-types"
        entityLabel="Órgano regional"
        entityEndpoint="regional-organs"
        filterParam="tipo_organo_regional"
        required
      />

      {/* Universidad (tipo de entidad → universidad en cascada) */}
      <CascadingEntityField
        control={control}
        name="universidad"
        typeLabel="Tipo de entidad universitaria"
        typeEndpoint="university-entity-types"
        entityLabel="Universidad"
        entityEndpoint="universities"
        filterParam="tipo_entidad"
        required
        toLabel={(row) => String(row.nombre ?? row.siglas ?? row.id)}
      />

      {/* Fecha de solicitud + Máximo de campos clínicos en una línea */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Controller
          control={control}
          name="fecha_solicitud"
          rules={{ required: "Campo obligatorio." }}
          render={({ field, fieldState }) => (
            <Row label="Fecha de solicitud" required error={fieldState.error?.message}>
              <DatePicker
                value={(field.value as string) ?? ""}
                onChange={(iso) => field.onChange(iso)}
                ariaInvalid={!!fieldState.error}
              />
            </Row>
          )}
        />
        <Controller
          control={control}
          name="max_campos_clinicos"
          rules={{
            validate: (v) =>
              !isEspecifico || (v !== "" && v != null)
                ? true
                : "Obligatorio para convenios Específicos.",
          }}
          render={({ field, fieldState }) => (
            <Row
              label="Máximo de campos clínicos (solo Específico)"
              required={isEspecifico}
              error={fieldState.error?.message}
            >
              <Input
                type="number"
                value={(field.value as string | number) ?? ""}
                onChange={(e) => field.onChange(e.target.value)}
                disabled={!isEspecifico}
                aria-invalid={!!fieldState.error}
              />
            </Row>
          )}
        />
      </div>

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

/** Fila etiqueta + control + error, reutilizada por los campos del formulario. */
function Row({
  label,
  required,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <Label>
        {label}
        {required ? " *" : ""}
      </Label>
      {children}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
