import { createElement } from "react";

import type { ColumnConfig, FilterConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { EntityLogo } from "@/components/ui/entity-logo";
import { LogoUploadField } from "@/components/catalogos/logo-upload-field";

const siNo = (v: unknown) => (v ? "Sí" : "No");


/** Lee `codigo` de un objeto `*_detalle` de FK (o «—»). */
const detalleCodigo = (v: unknown): string =>
  v && typeof v === "object" && "codigo" in v
    ? String((v as { codigo?: unknown }).codigo ?? "—")
    : "—";

/** Lee `nombre` de un objeto `*_detalle` de FK (o «—»). */
const detalleNombre = (v: unknown): string =>
  v && typeof v === "object" && "nombre" in v
    ? String((v as { nombre?: unknown }).nombre ?? "—")
    : "—";

/** Lee una parte del `ubigeo_detalle` (distrito/provincia/departamento) o «—». */
const ubigeoParte = (v: unknown, parte: "distrito" | "provincia" | "departamento"): string =>
  v && typeof v === "object" && parte in v
    ? String((v as Record<string, unknown>)[parte] ?? "—")
    : "—";

/** Etiqueta combinada de un objeto `ubigeo_detalle` (`{departamento, provincia, distrito}`). */
const ubigeoDetalleLabel = (v: unknown): string => {
  if (!v || typeof v !== "object") return "—";
  const u = v as Record<string, unknown>;
  return [u.departamento, u.provincia, u.distrito].filter(Boolean).join(", ") || "—";
};

/** Columna «Logo» reutilizable: muestra el logo de la entidad (o su fallback institucional). */
const logoColumn = (endpoint: string): ColumnConfig => ({
  key: "referencia_logo",
  header: "Logo",
  render: (r) =>
    createElement(EntityLogo, {
      entidad: endpoint,
      id: r.id,
      referenciaLogo: (r.referencia_logo as string | undefined) ?? null,
      size: 32,
    }),
});

/** Etiqueta legible de un ubigeo (no tiene `nombre`). */
const ubigeoLabel = (r: WithId) =>
  [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")]
    .filter(Boolean)
    .join(" — ");

/** Filtro `activo` reutilizable (boolean Sí/No). */
const activoFilter: FilterConfig = { name: "activo", label: "Activo", type: "boolean" };

/**
 * Configuración de las entidades organizacionales del módulo Convenios.
 * Fuente de verdad única: la consumen tanto `/convenios/maestros` como `/catalogos/entidades`.
 * Campos verificados contra el modelo del backend (ver `spec/catalogos.md` §5/R1).
 */
export const ENTITY_CONFIGS: Record<string, ResourceConfig> = {
  universities: {
    endpoint: "universities",
    title: "Universidades",
    singular: "universidad",
    createPrefix: "Nueva",
    description: "Entidades académicas registradas en RENADS.",
    searchPlaceholder: "Buscar por nombre, siglas o RUC…",
    // Logo embebido en la edición (solo universidades): se muestra sobre el formulario al editar.
    renderEditInfo: (r) =>
      createElement(LogoUploadField, {
        entidad: "universities",
        id: r.id,
        referenciaLogo: (r.referencia_logo as string | undefined) ?? null,
      }),
    columns: [
      logoColumn("universities"),
      { key: "nombre", header: "Nombre" },
      { key: "siglas", header: "Siglas" },
      {
        key: "tipo_gestion",
        header: "Gestión",
        render: (r) => detalleNombre(r.tipo_gestion_detalle),
      },
      {
        key: "tipo_entidad",
        header: "Tipo de entidad",
        render: (r) => detalleNombre(r.tipo_entidad_detalle),
      },
      {
        key: "tipo_autorizacion",
        header: "Autorización",
        render: (r) => detalleNombre(r.tipo_autorizacion_detalle),
      },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "tipo_gestion",
        label: "Tipo de gestión",
        type: "select",
        optionsEndpoint: "university-management-types",
      },
      {
        name: "tipo_entidad",
        label: "Tipo de entidad",
        type: "select",
        // El filtro por `organo` (id de "Universidad") lo inyecta la página en runtime
        // (los ids de `organs` dependen de la BD — nunca se hardcodean).
        optionsEndpoint: "organ-directories",
      },
      {
        name: "tipo_autorizacion",
        label: "Tipo de autorización",
        type: "select",
        optionsEndpoint: "authorization-types",
      },
      activoFilter,
    ],
    fields: [
      // ── Identificación institucional ──────────────────────────────────────
      { name: "_s1", label: "Identificación institucional", type: "separator" },
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      { name: "siglas", label: "Siglas", type: "text" },
      { name: "codigo_inei", label: "Código INEI", type: "text" },

      // ── Clasificación ─────────────────────────────────────────────────────
      { name: "_s2", label: "Clasificación", type: "separator" },
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
        // `optionsParams:{organo:<id de "Universidad">}` inyectado por la página (runtime).
        optionsEndpoint: "organ-directories",
      },
      {
        name: "tipo_autorizacion",
        label: "Tipo de autorización",
        type: "select",
        required: true,
        optionsEndpoint: "authorization-types",
      },

      // ── Resolución y vigencia ─────────────────────────────────────────────
      { name: "_s3", label: "Resolución y vigencia", type: "separator" },
      { name: "numero_resolucion", label: "Número de resolución", type: "text" },
      { name: "fecha_constitucion", label: "Fecha de constitución", type: "date" },
      { name: "fecha_autorizacion", label: "Fecha de autorización", type: "date" },

      // ── Contacto y ubicación ──────────────────────────────────────────────
      { name: "_s4", label: "Contacto y ubicación", type: "separator" },
      { name: "direccion_legal", label: "Dirección legal", type: "text", uppercase: false },
      { name: "telefono", label: "Teléfono", type: "text", uppercase: false },
      { name: "correo_institucional", label: "Correo institucional", type: "email", uppercase: false },
      {
        name: "ubigeo",
        label: "Ubigeo",
        type: "select",
        optionsEndpoint: "ubigeos",
        optionsToLabel: ubigeoLabel,
        optionsValueKey: "codigo", // PK textual (mig 0048-0049)
        optionsSearchable: true,
      },

      // ── Estado ────────────────────────────────────────────────────────────
      { name: "_s5", label: "Estado", type: "separator" },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  ipress: {
    endpoint: "ipress",
    title: "Establecimientos de Salud",
    singular: "Establecimiento de Salud",
    description: "Sedes docentes autorizadas para la prestación de servicios de salud.",
    // PK textual `codigo_renipress` (mig 0046-0047): editar/eliminar por `/ipress/<codigo>/`.
    pkField: "codigo_renipress",
    defaultOrdering: "codigo_renipress",
    searchPlaceholder: "Buscar por nombre o RENIPRESS…",
    columns: [
      logoColumn("ipress"),
      { key: "codigo_renipress", header: "Código" },
      { key: "nombre", header: "Establecimiento" },
      { key: "categoria", header: "Categoría", render: (r) => detalleCodigo(r.categoria_detalle) },
      {
        key: "tipo_clasificacion",
        header: "Clasificación",
        render: (r) => detalleCodigo(r.tipo_clasificacion_detalle),
      },
      {
        key: "ambito_geografico_sanitario",
        header: "Ámbito geográfico",
        render: (r) => detalleNombre(r.ambito_geografico_sanitario_detalle),
      },
      { key: "microred", header: "Microred", 
        render: (r) => detalleNombre(r.microred_detalle) },
      {
        key: "ubigeo_departamento",
        header: "Departamento",
        render: (r) => ubigeoParte(r.ubigeo_detalle, "departamento"),
      },      
      {
        key: "ubigeo_provincia",
        header: "Provincia",
        render: (r) => ubigeoParte(r.ubigeo_detalle, "provincia"),
      },
      {
        key: "ubigeo_distrito",
        header: "Distrito",
        render: (r) => ubigeoParte(r.ubigeo_detalle, "distrito"),
      },
      {
        key: "es_sede_docente",
        header: "Sede docente",
        render: (r) => siNo(r.es_sede_docente),
      },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "unidad_ejecutora",
        label: "Unidad ejecutora",
        type: "select",
        optionsEndpoint: "executing-units",
        optionsValueKey: "codigo",
        optionsSearchable: true,
        optionsToLabel: (r) => String(r.nombre ?? r.codigo ?? ""),
      },
      {
        name: "ambito_geografico_sanitario",
        label: "Ámbito geográfico sanitario",
        type: "select",
        optionsEndpoint: "health-geographic-scopes",
      },
      { name: "es_sede_docente", label: "Sede docente", type: "boolean" },
      activoFilter,
    ],
    // Campos verificados contra `IpressAuto` (OpenAPI). Requeridos por el backend: `nombre`,
    // `unidad_ejecutora`, `ambito_geografico_sanitario`. El resto son opcionales/anulables.
    // `es_sede_docente` NO se edita aquí: se otorga con la acción CONAPRES `autorizar-sede-docente`.
    fields: [
      // Identificación
      { name: "codigo_renipress", label: "Código RENIPRESS", type: "text", required: true },
      { name: "numero_ruc", label: "RUC (11 dígitos)", type: "text", uppercase: false },
      { name: "nombre", label: "Nombre", type: "text", required: true, fullWidth: true, uppercase: false },

      // Clasificación (catálogos)
      {
        name: "categoria",
        label: "Categoría",
        type: "select",
        optionsEndpoint: "categories",
      },
      {
        name: "tipo_clasificacion",
        label: "Tipo de clasificación",
        type: "select",
        optionsEndpoint: "classification-types",
      },
      // Organización / alcance sanitario
      {
        name: "ambito_geografico_sanitario",
        label: "Ámbito geográfico sanitario",
        type: "select",
        required: true,
        optionsEndpoint: "health-geographic-scopes",
      },
      {
        name: "unidad_ejecutora",
        label: "Unidad ejecutora",
        type: "select",
        required: true,
        optionsEndpoint: "executing-units",
        optionsValueKey: "codigo",
        optionsSearchable: true,
        optionsToLabel: (r) => String(r.nombre ?? r.codigo ?? ""),
      },
      {
        name: "microred",
        label: "Microred",
        type: "select",
        optionsEndpoint: "micro-networks",
      },
      // Ubicación
      { name: "direccion", label: "Dirección", type: "text", fullWidth: true, uppercase: false },
      {
        name: "ubigeo",
        label: "Ubigeo",
        type: "select",
        optionsEndpoint: "ubigeos",
        optionsToLabel: ubigeoLabel,
        optionsValueKey: "codigo", // PK textual (mig 0048-0049)
        optionsSearchable: true,
      },
      { name: "latitud", label: "Latitud", type: "text", uppercase: false },
      { name: "longitud", label: "Longitud", type: "text", uppercase: false },
      // Capacidad / estado
      { name: "cantidad_camas", label: "Cantidad de camas", type: "number" },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "regional-governments": {
    endpoint: "regional-governments",
    title: "Gobiernos regionales",
    singular: "gobierno regional",
    searchPlaceholder: "Buscar por nombre…",
    columns: [
      logoColumn("regional-governments"),
      { key: "nombre", header: "Nombre" },
      { key: "sigla", header: "Sigla" },
      { key: "numero_ruc", header: "RUC" },
      { key: "telefono", header: "Teléfono" },
      { key: "ubigeo_detalle", header: "Ubicación", render: (r) => ubigeoDetalleLabel(r.ubigeo_detalle) },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
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
      activoFilter,
    ],
    fields: [
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      { name: "sigla", label: "Sigla", type: "text", uppercase: false },
      {
        name: "region",
        label: "Región",
        type: "select",
        required: true,
        optionsEndpoint: "regions",
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
      { name: "numero_ruc", label: "RUC (11 dígitos)", type: "text", uppercase: false },
      { name: "direccion", label: "Dirección", type: "text", uppercase: false },
      { name: "correo", label: "Correo institucional", type: "email", uppercase: false },
      { name: "telefono", label: "Teléfono", type: "text", uppercase: false },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  // Refactor 2026-09-08 (mig 0043-0045): PK = `codigo` (string4); fuera tipo_organo/
  // gobierno_regional/direccion/ubigeo/logo; entra `ambito_geografico_sanitario`.
  "executing-units": {
    endpoint: "executing-units",
    title: "Unidades ejecutoras",
    singular: "unidad ejecutora",
    createPrefix: "Nueva",
    pkField: "codigo",
    defaultOrdering: "codigo",
    searchPlaceholder: "Buscar por nombre o código…",
    columns: [
      { key: "codigo", header: "Código" },
      { key: "nombre", header: "Nombre" },
      {
        key: "ambito_geografico_sanitario",
        header: "Ámbito geográfico sanitario",
        render: (r) => detalleNombre(r.ambito_geografico_sanitario_detalle),
      },
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
    // `codigo` es la PK que provee el cliente en el alta; no se cambia en edición.
    createFields: [
      { name: "codigo", label: "Código (4 dígitos)", type: "text", required: true, uppercase: false },
      { name: "nombre", label: "Nombre", type: "text", required: true, fullWidth: true, uppercase: false },
      {
        name: "ambito_geografico_sanitario",
        label: "Ámbito geográfico sanitario",
        type: "select",
        required: true,
        optionsEndpoint: "health-geographic-scopes",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
    editFields: [
      { name: "codigo", label: "Código (4 dígitos)", type: "text", disabled: true, uppercase: false },
      { name: "nombre", label: "Nombre", type: "text", required: true, fullWidth: true, uppercase: false },
      {
        name: "ambito_geografico_sanitario",
        label: "Ámbito geográfico sanitario",
        type: "select",
        required: true,
        optionsEndpoint: "health-geographic-scopes",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
    fields: [],
  },

  "organ-directories": {
    endpoint: "organ-directories",
    title: "Órganos del directorio",
    singular: "órgano del directorio",
    description: "Directorio unificado: órganos del MINSA, Gobiernos Regionales, DIRIS y Unidades Ejecutoras.",
    searchPlaceholder: "Buscar por nombre o siglas…",
    columns: [
      {
        key: "organo",
        header: "Órgano",
        render: (r) => detalleNombre(r.organo_detalle),
      },
      { key: "nombre", header: "Nombre" },
      { key: "siglas", header: "Siglas" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "organo",
        label: "Órgano",
        type: "select",
        optionsEndpoint: "organs",
        optionsToLabel: (o) => String(o.nombre ?? o.id),
      },
      activoFilter,
    ],
    fields: [
      {
        name: "organo",
        label: "Órgano",
        type: "select",
        required: true,
        optionsEndpoint: "organs",
        optionsToLabel: (o) => String(o.nombre ?? o.id),
      },
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      { name: "siglas", label: "Siglas", type: "text" },
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
    filters: [activoFilter],
    fields: [
      { name: "nombre", label: "Denominación", type: "text", required: true, uppercase: false },
      { name: "descripcion", label: "Descripción", type: "text", uppercase: false },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
};

/** Orden y rótulos para el índice de maestros de Convenios. */
export const ENTITY_MENU: { slug: string; title: string }[] = [
  { slug: "universities", title: "Universidades" },
  { slug: "ipress", title: "IPRESS" },
  { slug: "regional-governments", title: "Gobiernos regionales" },
  { slug: "organ-directories", title: "Órganos del directorio" },
  { slug: "executing-units", title: "Unidades ejecutoras" },
  { slug: "conapres", title: "CONAPRES" },
];
