import React from "react";
import type { FilterConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { ENTITY_CONFIGS } from "@/lib/convenios/entities";
import { ActiveSwitchCell } from "@/lib/catalogos/active-switch-cell";
import { EntityLogo } from "@/components/ui/entity-logo";

const siNo = (v: unknown) => (v ? "Sí" : "No");

/** Lee `nombre` de un objeto `*_detalle` de FK (o «—»). */
const detalleNombre = (v: unknown): string =>
  v && typeof v === "object" && "nombre" in v
    ? String((v as { nombre?: unknown }).nombre ?? "—")
    : "—";

/** Etiqueta legible de un ubigeo (no tiene `nombre`). */
const ubigeoLabel = (r: WithId) =>
  [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")]
    .filter(Boolean)
    .join(" — ");

/** Etiqueta legible de un objeto `ubigeo_detalle` (`{departamento, provincia, distrito}`). */
const ubigeoDetalleLabel = (v: unknown): string => {
  if (!v || typeof v !== "object") return "—";
  const u = v as Record<string, unknown>;
  return [u.departamento, u.provincia, u.distrito].filter(Boolean).join(", ") || "—";
};

const activoFilter: FilterConfig = { name: "activo", label: "Activo", type: "boolean" };

/**
 * Entidades académicas (universidad) propias de `/catalogos`. Campos exactos según
 * `spec/catalogos.md` §5/R1. Escritura solo `Administrador RENADS` (default de `ResourceCrud`).
 */
const ACADEMIC_ENTITY_CONFIGS: Record<string, ResourceConfig> = {
  faculties: {
    endpoint: "faculties",
    title: "Facultades",
    singular: "facultad",
    createPrefix: "Nueva",
    description: "Facultades por universidad.",
    searchPlaceholder: "Buscar por nombre o dirección…",
    columns: [
      {
        key: "referencia_logo",
        header: "Logo",
        render: (r) =>
          React.createElement(EntityLogo, {
            entidad: "faculties",
            id: r.id,
            referenciaLogo: (r.referencia_logo as string | undefined) ?? null,
            size: 32,
          }),
      },
      { key: "nombre", header: "Nombre" },
      { key: "ubigeo_detalle", header: "Ubicación", render: (r) => ubigeoDetalleLabel(r.ubigeo_detalle) },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "universidad",
        label: "Universidad",
        type: "select",
        optionsEndpoint: "universities",
      },
      {
        name: "ubigeo",
        label: "Ubigeo",
        type: "select",
        optionsEndpoint: "ubigeos",
        optionsToLabel: ubigeoLabel,
        optionsValueKey: "codigo", // PK textual (mig 0048-0049)
        optionsSearchable: true,
      },
      activoFilter,
    ],
    fields: [
      {
        name: "universidad",
        label: "Universidad",
        type: "select",
        required: true,
        optionsEndpoint: "universities",
      },
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      { name: "direccion", label: "Dirección", type: "text", uppercase: false },
      {
        name: "ubigeo",
        label: "Ubigeo",
        type: "select",
        optionsEndpoint: "ubigeos",
        optionsToLabel: ubigeoLabel,
        optionsValueKey: "codigo", // PK textual (mig 0048-0049)
        optionsSearchable: true,
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "professional-careers": {
    endpoint: "professional-careers",
    title: "Carreras profesionales",
    singular: "carrera profesional",
    createPrefix: "Nueva",
    description: "Carreras, segundas especialidades, maestrías y doctorados.",
    searchPlaceholder: "Buscar por nombre…",
    containerClassName: "max-w-2xl",
    defaultOrdering: "orden",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "orden", header: "Orden" },
      {
        key: "activo",
        header: "Activo",
        render: (r) =>
          React.createElement(ActiveSwitchCell, {
            row: r,
            endpoint: "professional-careers",
          }),
      },
    ],
    filters: [
      {
        name: "nivel_academico",
        label: "Nivel académico",
        type: "select",
        optionsEndpoint: "academic-levels",
      },
      activoFilter,
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      {
        name: "nivel_academico",
        label: "Nivel académico",
        type: "select",
        required: true,
        optionsEndpoint: "academic-levels",
      },
      { name: "orden", label: "Orden", type: "number", defaultValue: 0 },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "university-campuses": {
    endpoint: "university-campuses",
    title: "Sedes universitarias",
    singular: "sede universitaria",
    createPrefix: "Nueva",
    description: "Sedes/filiales por universidad.",
    searchPlaceholder: "Buscar por nombre…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "universidad",
        label: "Universidad",
        type: "select",
        optionsEndpoint: "universities",
      },
      { name: "region", label: "Región", type: "select", optionsEndpoint: "regions" },
      activoFilter,
    ],
    fields: [
      {
        name: "universidad",
        label: "Universidad",
        type: "select",
        required: true,
        optionsEndpoint: "universities",
      },
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      { name: "direccion", label: "Dirección", type: "text", uppercase: false },
      { name: "region", label: "Región", type: "select", optionsEndpoint: "regions" },
      {
        name: "ubigeo",
        label: "Ubigeo",
        type: "select",
        optionsEndpoint: "ubigeos",
        optionsToLabel: ubigeoLabel,
        optionsValueKey: "codigo", // PK textual (mig 0048-0049)
        optionsSearchable: true,
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

};

/**
 * Entidades de la estructura sanitaria (jerarquía `health-geographic-scopes` → `networks` →
 * `micro-networks`). CRUD con FK; escritura solo `Administrador RENADS` (default de `ResourceCrud`).
 */
const SANITARY_ENTITY_CONFIGS: Record<string, ResourceConfig> = {
  networks: {
    endpoint: "networks",
    title: "Redes",
    singular: "red",
    createPrefix: "Nueva",
    description: "Redes asistenciales por ámbito geográfico sanitario.",
    searchPlaceholder: "Buscar por código o nombre…",
    columns: [
      { key: "codigo", header: "Código" },
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "ambito_geografico_sanitario",
        label: "Ámbito geográfico sanitario",
        type: "select",
        optionsEndpoint: "health-geographic-scopes",
      },
      activoFilter,
    ],
    fields: [
      { name: "codigo", label: "Código", type: "text", required: true },
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      {
        name: "ambito_geografico_sanitario",
        label: "Ámbito geográfico sanitario",
        type: "select",
        required: true,
        optionsEndpoint: "health-geographic-scopes",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "micro-networks": {
    endpoint: "micro-networks",
    title: "Microrredes",
    singular: "microrred",
    createPrefix: "Nueva",
    description: "Microrredes por red asistencial.",
    searchPlaceholder: "Buscar por código o nombre…",
    columns: [
      { key: "codigo", header: "Código" },
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    // Filtro de lista plano (la cascada ámbito→red aplica solo al formulario de alta/edición).
    filters: [
      { name: "red", label: "Red", type: "select", optionsEndpoint: "networks" },
      activoFilter,
    ],
    fields: [
      // Campo virtual (solo UI, no se envía): filtra el select `red` por ámbito y lo resetea al cambiar.
      {
        name: "_ambito",
        label: "Ámbito geográfico sanitario",
        type: "select",
        virtual: true,
        optionsEndpoint: "health-geographic-scopes",
      },
      {
        name: "red",
        label: "Red",
        type: "select",
        required: true,
        optionsEndpoint: "networks",
        optionsParamsFrom: (v): Record<string, string> =>
          v._ambito ? { ambito_geografico_sanitario: String(v._ambito) } : {},
        resetsOn: ["_ambito"],
      },
      { name: "codigo", label: "Código", type: "text", required: true },
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
};

/**
 * Registro único de entidades organizacionales/académicas de `/catalogos`. Reutiliza las 7 configs
 * de Convenios (`ENTITY_CONFIGS`) sin duplicarlas y añade las académicas, sanitarias y el puente
 * de directorio↔cargos.
 */
export const CATALOGO_ENTITY_CONFIGS: Record<string, ResourceConfig> = {
  ...ENTITY_CONFIGS,
  ...ACADEMIC_ENTITY_CONFIGS,
  ...SANITARY_ENTITY_CONFIGS,
};

/** Orden y rótulos del índice de entidades de `/catalogos`. */
export const CATALOGO_ENTITY_MENU: { slug: string; title: string }[] = [
  { slug: "universities", title: "Universidades" },
  { slug: "faculties", title: "Facultades" },
  { slug: "professional-careers", title: "Carreras Profesionales" },
  { slug: "university-careers", title: "Carreras por Facultad y Universidad" },
  { slug: "university-campuses", title: "Sedes Universitarias" },
  { slug: "ipress", title: "Establecimientos de Salud" },
  { slug: "regional-governments", title: "Gobiernos Regionales" },
  { slug: "organ-directories", title: "Órganos del Directorio" },
  { slug: "executing-units", title: "Unidades Ejecutoras" },
  { slug: "networks", title: "Redes" },
  { slug: "micro-networks", title: "Microrredes" },
  { slug: "conapres", title: "CONAPRES" },
];
