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
import { useOrgans, organIdByNombre, ORGAN_NOMBRE } from "@/lib/catalogos/organs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * Formulario de alta de convenio con reglas de negocio Marco/Específico:
 * - `tipo_convenio` se bloquea una vez elegido.
 * - `convenio_marco`, `max_campos_clinicos`, `unidad_ejecutora` y `facultad`
 *   solo aplican a Específico.
 * - **Órgano (categoría)** `_organo` (virtual, no se envía) filtra `organic-units`
 *   por `?organo=<id>`. Para un **Marco** solo se ofrecen las categorías que pueden
 *   solicitarlo (RN-1: Gobierno Regional / MINSA / Universidad).
 * - `gobierno_regional` es **obligatorio** solo en Marco + órgano Gobierno Regional; en
 *   cualquier otro caso va nulo (el backend lo rechaza si se envía — RN-GORE).
 * - `facultad` se filtra por universidad.
 * - `nomenclatura` es asignada por DIGEP; no editable en el alta.
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
  const { control, handleSubmit, setValue, watch } = useForm<FormValues>({
    defaultValues: {
      tipo_convenio: null,
      titulo: "",
      plantilla: null,
      convenio_marco: null,
      solicitante_tipo_contenido: null,
      solicitante_id_objeto: null,
      _organo: null,
      unidad_organica: null,
      gobierno_regional: null,
      universidad: null,
      unidad_ejecutora: null,
      facultad: null,
      fecha_solicitud: "",
      max_campos_clinicos: "",
    },
  });

  const tipoId = useWatch({ control, name: "tipo_convenio" }) as number | null;
  const organoCat = useWatch({ control, name: "_organo" }) as number | null;
  const universidadId = watch("universidad") as number | null;

  // Catálogo de tipos para detectar si es Específico.
  const typesQuery = useQuery({
    queryKey: ["convention-types", "all"],
    queryFn: () => searchResource("convention-types"),
    staleTime: 5 * 60_000,
  });
  const selected = typesQuery.data?.find((t) => t.id === tipoId);
  const isEspecifico =
    !!selected &&
    /espec/i.test(String(selected.nombre ?? selected.codigo ?? ""));
  const isMarco = tipoId != null && !isEspecifico;

  // Tipo «Marco» (id resuelto por nombre) para acotar el combo de convenio marco a Marcos.
  const marcoTypeId = (typesQuery.data ?? []).find((t) =>
    /marco/i.test(String(t.nombre ?? t.codigo ?? "")),
  )?.id;
  // Estados con vigencia (RN-3, espejo de `ESTADOS_VIGENTES` del backend) — un Específico solo
  // depende de un Marco en uno de estos estados.
  const ESTADOS_MARCO_VIGENTE = new Set(["VIGENTE", "PUBLICADO", "SUSCRITO"]);

  const tipoItems = (typesQuery.data ?? []).map((t) => ({
    value: String(t.id),
    label: String(t.nombre ?? t.codigo ?? t.id),
  }));

  // Catálogo canónico `organs` (categoría del órgano del directorio, discriminador FK `organo`).
  const organsQuery = useOrgans();
  const goreId = organIdByNombre(organsQuery.data, ORGAN_NOMBRE.GORE);
  // RN-1: un Marco solo lo solicita Gobierno Regional, MINSA o Universidad. En Específico se
  // ofrecen todas las categorías (el backend valida la coherencia final).
  const marcoNombres: string[] = [
    ORGAN_NOMBRE.GORE,
    ORGAN_NOMBRE.MINSA,
    ORGAN_NOMBRE.UNIVERSIDAD,
  ];
  const orgItems = (organsQuery.data ?? [])
    .filter((o) => !isMarco || marcoNombres.includes(o.nombre))
    .map((o) => ({ value: String(o.id), label: o.nombre }));

  // `gobierno_regional` solo aplica a Marco + órgano de categoría Gobierno Regional (RN-GORE).
  const mostrarGORE = isMarco && goreId != null && organoCat === goreId;

  useEffect(() => {
    if (!isEspecifico) {
      setValue("convenio_marco", null);
      setValue("max_campos_clinicos", "");
      setValue("unidad_ejecutora", null);
      setValue("facultad", null);
    }
  }, [isEspecifico, setValue]);

  // Al cambiar la categoría del órgano: resetear el órgano del directorio (cascada) y, si ya no
  // corresponde GORE, limpiarlo.
  useEffect(() => {
    setValue("unidad_organica", null);
  }, [organoCat, setValue]);

  useEffect(() => {
    if (!mostrarGORE) setValue("gobierno_regional", null);
  }, [mostrarGORE, setValue]);

  // Resetear facultad al cambiar universidad.
  useEffect(() => {
    setValue("facultad", null);
  }, [universidadId, setValue]);

  function submit(values: FormValues) {
    const payload: FormValues = {
      tipo_convenio: Number(values.tipo_convenio),
      titulo: values.titulo,
      solicitante_tipo_contenido: Number(values.solicitante_tipo_contenido),
      solicitante_id_objeto: Number(values.solicitante_id_objeto),
      unidad_organica: Number(values.unidad_organica),
      universidad: Number(values.universidad),
      fecha_solicitud: values.fecha_solicitud,
    };
    if (values.plantilla != null) payload.plantilla = Number(values.plantilla);
    if (values.gobierno_regional != null)
      payload.gobierno_regional = Number(values.gobierno_regional);
    if (isEspecifico) {
      if (values.convenio_marco != null)
        payload.convenio_marco = Number(values.convenio_marco);
      if (values.max_campos_clinicos !== "" && values.max_campos_clinicos != null)
        payload.max_campos_clinicos = Number(values.max_campos_clinicos);
      if (values.unidad_ejecutora != null && values.unidad_ejecutora !== "")
        payload.unidad_ejecutora = values.unidad_ejecutora; // PK textual (codigo), sin Number()
      if (values.facultad != null)
        payload.facultad = Number(values.facultad);
    }
    onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="grid gap-4">
      {/* Tipo de convenio */}
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

      {/* Título */}
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

      {/* Nomenclatura (read-only; la asigna DIGEP en la evaluación técnica) */}
      <Row label="Nomenclatura">
        <Input disabled placeholder="Se asigna en la evaluación técnica (DIGEP)" />
      </Row>

      {/* Plantilla */}
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
              params={
                isEspecifico && marcoTypeId != null
                  ? { tipo_convenio: String(marcoTypeId) }
                  : undefined
              }
              // Solo Marcos con vigencia (suscrito/publicado/vigente); se muestra la nomenclatura.
              filterRows={(row: WithId) =>
                ESTADOS_MARCO_VIGENTE.has(String(row.estado_codigo ?? ""))
              }
              toLabel={(row: WithId) => String(row.nomenclatura || row.titulo || row.id)}
              value={field.value as number | null}
              onChange={(v) => field.onChange(v)}
              disabled={!isEspecifico}
              placeholder={isEspecifico ? "Buscar convenio marco…" : "Solo para Específico"}
            />
          </Row>
        )}
      />

      {/* Entidad solicitante */}
      <SolicitanteField control={control} />

      {/* Categoría del órgano (discriminador `organo`) — filtra el órgano del directorio.
          Virtual: no se envía al backend. */}
      <Controller
        control={control}
        name="_organo"
        rules={{ validate: (v) => (v != null && v !== "") || "Campo obligatorio." }}
        render={({ field, fieldState }) => (
          <Row label="Categoría del órgano" required error={fieldState.error?.message}>
            <Select
              items={orgItems}
              value={field.value != null ? String(field.value) : null}
              onValueChange={(v: string | null) =>
                field.onChange(v ? Number(v) : null)
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar categoría…" />
              </SelectTrigger>
              <SelectContent>
                {orgItems.map((i) => (
                  <SelectItem key={i.value} value={i.value}>
                    {i.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Row>
        )}
      />

      {/* Unidad orgánica — filtrada por la categoría elegida (`?organo=<id>`) */}
      <Controller
        control={control}
        name="unidad_organica"
        rules={{ validate: (v) => (v != null && v !== "") || "Campo obligatorio." }}
        render={({ field, fieldState }) => (
          <Row label="Unidad orgánica" required error={fieldState.error?.message}>
            <EntityCombobox
              key={organoCat ?? 0}
              endpoint="organic-units"
              params={organoCat != null ? { organo: String(organoCat) } : undefined}
              value={field.value as number | null}
              onChange={(v) => field.onChange(v)}
              disabled={organoCat == null}
              placeholder={
                organoCat == null
                  ? "Elige primero la categoría…"
                  : "Buscar unidad orgánica…"
              }
            />
          </Row>
        )}
      />

      {/* Gobierno regional — obligatorio solo en Marco + órgano Gobierno Regional (RN-GORE) */}
      {mostrarGORE ? (
        <Controller
          control={control}
          name="gobierno_regional"
          rules={{ validate: (v) => (v != null && v !== "") || "Campo obligatorio." }}
          render={({ field, fieldState }) => (
            <Row label="Gobierno regional" required error={fieldState.error?.message}>
              <EntityCombobox
                endpoint="regional-governments"
                toLabel={(row: WithId) => String(row.nombre ?? row.sigla ?? row.id)}
                value={field.value as number | null}
                onChange={(v) => field.onChange(v)}
                placeholder="Buscar gobierno regional…"
              />
            </Row>
          )}
        />
      ) : null}

      {/* Universidad */}
      <Controller
        control={control}
        name="universidad"
        rules={{ validate: (v) => (v != null && v !== "") || "Campo obligatorio." }}
        render={({ field, fieldState }) => (
          <Row label="Universidad" required error={fieldState.error?.message}>
            <EntityCombobox
              endpoint="universities"
              toLabel={(row: WithId) => String(row.nombre ?? row.siglas ?? row.id)}
              value={field.value as number | null}
              onChange={(v) => field.onChange(v)}
              placeholder="Buscar universidad…"
            />
          </Row>
        )}
      />

      {/* Unidad ejecutora — solo Específico */}
      <Controller
        control={control}
        name="unidad_ejecutora"
        render={({ field }) => (
          <Row label="Unidad ejecutora (solo Específico)">
            <EntityCombobox
              endpoint="executing-units"
              valueKey="codigo"
              toLabel={(r) => String(r.nombre ?? r.codigo ?? "")}
              value={field.value as string | null}
              onChange={(v) => field.onChange(v)}
              disabled={!isEspecifico}
              placeholder={isEspecifico ? "Buscar unidad ejecutora…" : "Solo para Específico"}
            />
          </Row>
        )}
      />

      {/* Facultad — solo Específico, filtrada por universidad */}
      <Controller
        control={control}
        name="facultad"
        render={({ field }) => (
          <Row label="Facultad (solo Específico)">
            <EntityCombobox
              key={universidadId ?? 0}
              endpoint="faculties"
              params={universidadId ? { universidad: String(universidadId) } : undefined}
              value={field.value as number | null}
              onChange={(v) => field.onChange(v)}
              disabled={!isEspecifico || !universidadId}
              placeholder={
                !isEspecifico
                  ? "Solo para Específico"
                  : !universidadId
                  ? "Elige primero universidad…"
                  : "Buscar facultad…"
              }
            />
          </Row>
        )}
      />

      {/* Fecha de solicitud + Máximo campos de formación */}
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
              label="Máximo de campos de formación (solo Específico)"
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
