import type { FilterConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { ENTITY_CONFIGS } from "@/lib/convenios/entities";

const siNo = (v: unknown) => (v ? "Sí" : "No");

/** Etiqueta legible de un ubigeo (no tiene `nombre`). */
const ubigeoLabel = (r: WithId) =>
  [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")]
    .filter(Boolean)
    .join(" — ");

const activoFilter: FilterConfig = { name: "activo", label: "Activo", type: "boolean" };

/**
 * Entidades académicas (universidad) propias de `/catalogos`. Campos exactos según
 * `spec/catalogos.md` §5/R1. Escritura solo `Administrador RENADS` (default de `ResourceCrud`).
 */
const ACADEMIC_ENTITY_CONFIGS: Record<string, ResourceConfig> = {
  "university-authorities": {
    endpoint: "university-authorities",
    title: "Autoridades universitarias",
    singular: "autoridad universitaria",
    description: "Autoridades vigentes por universidad.",
    searchPlaceholder: "Buscar por nombre o cargo…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "cargo", header: "Cargo" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "universidad",
        label: "Universidad",
        type: "select",
        optionsEndpoint: "universities",
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
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "cargo", label: "Cargo", type: "text", required: true },
      { name: "fecha_inicio_cargo", label: "Inicio del cargo", type: "date", required: true },
      { name: "fecha_fin_cargo", label: "Fin del cargo", type: "date" },
      { name: "numero_resolucion", label: "Número de resolución", type: "text" },
      {
        name: "referencia_documento_resolucion",
        label: "Referencia del documento de resolución",
        type: "text",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  faculties: {
    endpoint: "faculties",
    title: "Facultades",
    singular: "facultad",
    description: "Facultades por universidad.",
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
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "professional-careers": {
    endpoint: "professional-careers",
    title: "Carreras profesionales",
    singular: "carrera profesional",
    // Contrato backend (`ProfessionalCareerAuto`): solo `nombre`, `nivel_academico` y `activo`.
    // El nivel académico distingue carrera / segunda especialidad / maestría / doctorado.
    description: "Carreras, segundas especialidades, maestrías y doctorados.",
    searchPlaceholder: "Buscar por nombre…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
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
      { name: "nombre", label: "Nombre", type: "text", required: true },
      {
        name: "nivel_academico",
        label: "Nivel académico",
        type: "select",
        required: true,
        optionsEndpoint: "academic-levels",
      },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

  "university-campuses": {
    endpoint: "university-campuses",
    title: "Sedes universitarias",
    singular: "sede universitaria",
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
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "direccion", label: "Dirección", type: "text" },
      { name: "region", label: "Región", type: "select", optionsEndpoint: "regions" },
      {
        name: "ubigeo",
        label: "Ubigeo",
        type: "select",
        optionsEndpoint: "ubigeos",
        optionsToLabel: ubigeoLabel,
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
      { name: "nombre", label: "Nombre", type: "text", required: true },
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
      { name: "nombre", label: "Nombre", type: "text", required: true },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
};

/**
 * Registro único de entidades organizacionales/académicas de `/catalogos`. Reutiliza las 7 configs
 * de Convenios (`ENTITY_CONFIGS`) sin duplicarlas y añade las académicas y las sanitarias.
 */
export const CATALOGO_ENTITY_CONFIGS: Record<string, ResourceConfig> = {
  ...ENTITY_CONFIGS,
  ...ACADEMIC_ENTITY_CONFIGS,
  ...SANITARY_ENTITY_CONFIGS,
};

/** Orden y rótulos del índice de entidades de `/catalogos`. */
export const CATALOGO_ENTITY_MENU: { slug: string; title: string }[] = [
  { slug: "universities", title: "Universidades" },
  { slug: "university-authorities", title: "Autoridades Universitarias" },
  { slug: "faculties", title: "Facultades" },
  { slug: "professional-careers", title: "Carreras Profesionales" },
  { slug: "university-campuses", title: "Sedes Universitarias" },
  { slug: "ipress", title: "IPRESS" },
  { slug: "regional-governments", title: "Gobiernos Regionales" },
  { slug: "executing-units", title: "Unidades Ejecutoras" },
  { slug: "regional-organs", title: "Órganos Regionales" },
  { slug: "minsa-organs", title: "Órganos MINSA" },
  { slug: "networks", title: "Redes" },
  { slug: "micro-networks", title: "Microrredes" },
  { slug: "conapres", title: "CONAPRES" },
];
