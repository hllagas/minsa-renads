import type { ResourceConfig } from "@/lib/crud/types";

const siNo = (v: unknown) => (v ? "Sí" : "No");

/** Configuración de las entidades maestras del módulo Convenios (Pase 1). */
export const ENTITY_CONFIGS: Record<string, ResourceConfig> = {
  universities: {
    endpoint: "universities",
    title: "Universidades",
    singular: "universidad",
    description: "Entidades académicas registradas en RENADS.",
    searchPlaceholder: "Buscar por nombre o siglas…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "siglas", header: "Siglas" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "siglas", label: "Siglas", type: "text" },
      { name: "codigo_inei", label: "Código INEI", type: "text" },
      { name: "direccion_legal", label: "Dirección legal", type: "text" },
      { name: "telefono", label: "Teléfono", type: "text" },
      { name: "correo_institucional", label: "Correo institucional", type: "email" },
      {
        name: "tipo_gestion",
        label: "Tipo de gestión",
        type: "select",
        required: true,
        optionsEndpoint: "university-management-types",
      },
      {
        name: "tipo_entidad",
        label: "Tipo de entidad",
        type: "select",
        required: true,
        optionsEndpoint: "university-entity-types",
      },
      {
        name: "tipo_autorizacion",
        label: "Tipo de autorización",
        type: "select",
        required: true,
        optionsEndpoint: "authorization-types",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  ipress: {
    endpoint: "ipress",
    title: "IPRESS",
    singular: "IPRESS",
    description: "Establecimientos de salud (sedes).",
    searchPlaceholder: "Buscar por nombre o RENIPRESS…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "codigo_renipress", header: "RENIPRESS" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "codigo_renipress", label: "Código RENIPRESS", type: "text" },
      { name: "direccion", label: "Dirección", type: "text" },
      {
        name: "unidad_ejecutora",
        label: "Unidad ejecutora",
        type: "select",
        required: true,
        optionsEndpoint: "executing-units",
      },
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

  "regional-governments": {
    endpoint: "regional-governments",
    title: "Gobiernos regionales",
    singular: "gobierno regional",
    searchPlaceholder: "Buscar por nombre…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true },
      {
        name: "region",
        label: "Región",
        type: "select",
        required: true,
        optionsEndpoint: "regions",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "executing-units": {
    endpoint: "executing-units",
    title: "Unidades ejecutoras",
    singular: "unidad ejecutora",
    searchPlaceholder: "Buscar por nombre o código…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "codigo", header: "Código" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "codigo", label: "Código presupuestal", type: "text" },
      { name: "direccion", label: "Dirección", type: "text" },
      {
        name: "organo_regional",
        label: "Órgano regional",
        type: "select",
        required: true,
        optionsEndpoint: "regional-organs",
      },
      {
        name: "tipo_unidad_ejecutora",
        label: "Tipo de unidad ejecutora",
        type: "select",
        required: true,
        optionsEndpoint: "executing-unit-types",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "regional-organs": {
    endpoint: "regional-organs",
    title: "Órganos regionales",
    singular: "órgano regional",
    searchPlaceholder: "Buscar por nombre o siglas…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "siglas", header: "Siglas" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "siglas", label: "Siglas", type: "text" },
      { name: "direccion", label: "Dirección", type: "text" },
      {
        name: "gobierno_regional",
        label: "Gobierno regional",
        type: "select",
        required: true,
        optionsEndpoint: "regional-governments",
      },
      {
        name: "tipo_organo_regional",
        label: "Tipo de órgano regional",
        type: "select",
        required: true,
        optionsEndpoint: "regional-organ-types",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "minsa-organs": {
    endpoint: "minsa-organs",
    title: "Órganos MINSA",
    singular: "órgano MINSA",
    searchPlaceholder: "Buscar por nombre o siglas…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "siglas", header: "Siglas" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "siglas", label: "Siglas", type: "text" },
      {
        name: "tipo_organo_minsa",
        label: "Tipo de órgano MINSA",
        type: "select",
        required: true,
        optionsEndpoint: "minsa-organ-types",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  conapres: {
    endpoint: "conapres",
    title: "CONAPRES",
    singular: "CONAPRES",
    searchPlaceholder: "Buscar por nombre…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    fields: [
      { name: "nombre", label: "Denominación", type: "text", required: true },
      { name: "descripcion", label: "Descripción", type: "text" },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
};

/** Orden y rótulos para el índice de maestros. */
export const ENTITY_MENU: { slug: string; title: string }[] = [
  { slug: "universities", title: "Universidades" },
  { slug: "ipress", title: "IPRESS" },
  { slug: "regional-governments", title: "Gobiernos regionales" },
  { slug: "executing-units", title: "Unidades ejecutoras" },
  { slug: "regional-organs", title: "Órganos regionales" },
  { slug: "minsa-organs", title: "Órganos MINSA" },
  { slug: "conapres", title: "CONAPRES" },
];
