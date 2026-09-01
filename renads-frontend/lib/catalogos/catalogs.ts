import type { FilterConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

const siNo = (v: unknown) => (v ? "Sí" : "No");

const detalleNombre = (v: unknown): string =>
  v && typeof v === "object" && "nombre" in v
    ? String((v as { nombre?: unknown }).nombre ?? "—")
    : "—";

const activoFilter: FilterConfig = { name: "activo", label: "Activo", type: "boolean" };

/**
 * Catálogo estándar de solo lectura: columnas `codigo`/`nombre`/`activo`, filtro `activo`,
 * search `codigo`/`nombre`, ordering por defecto `id`. La escritura está fuera de alcance
 * (los catálogos ya están poblados/validados en el backend).
 */
function readOnlyCatalog(
  endpoint: string,
  title: string,
  singular: string,
): ResourceConfig {
  return {
    endpoint,
    title,
    singular,
    readOnly: true,
    searchPlaceholder: "Buscar por código o nombre…",
    columns: [
      { key: "codigo", header: "Código" },
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [activoFilter],
    fields: [], // sin escritura
  };
}

/**
 * Catálogo maestro con **CRUD** (RNF-MAN-01/02/03): mismas columnas/búsqueda que el de solo
 * lectura, pero editable. Escritura restringida a `Administrador RENADS` (backend
 * `IsAdminRoleOrReadOnly` + auditoría). Campos del modelo base `Catalog`: `codigo` (único,
 * obligatorio), `nombre` (obligatorio) y `activo`.
 */
function writableCatalog(
  endpoint: string,
  title: string,
  singular: string,
): ResourceConfig {
  return {
    endpoint,
    title,
    singular,
    writeRoles: ["Administrador RENADS"],
    searchPlaceholder: "Buscar por código o nombre…",
    columns: [
      { key: "codigo", header: "Código" },
      { key: "nombre", header: "Nombre" },
      { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
    ],
    filters: [activoFilter],
    fields: [
      { name: "codigo", label: "Código", type: "text", required: true },
      { name: "nombre", label: "Nombre", type: "text", required: true, uppercase: false },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  };
}

/** Catálogo de ubigeos (INEI): columnas y filtros geográficos propios. */
const ubigeosConfig: ResourceConfig = {
  endpoint: "ubigeos",
  title: "Ubigeos",
  singular: "ubigeo",
  readOnly: true,
  description: "Catálogo geográfico INEI (departamento / provincia / distrito).",
  searchPlaceholder: "Buscar por código, distrito, provincia o departamento…",
  columns: [
    { key: "codigo", header: "Código" },
    { key: "departamento", header: "Departamento" },
    { key: "provincia", header: "Provincia" },
    { key: "distrito", header: "Distrito" },
    { key: "activo", header: "Activo", render: (r: WithId) => siNo(r.activo) },
  ],
  filters: [
    { name: "departamento", label: "Departamento", type: "text" },
    { name: "provincia", label: "Provincia", type: "text" },
    { name: "distrito", label: "Distrito", type: "text" },
    activoFilter,
  ],
  fields: [],
};

/** Registro de los 18 catálogos de solo lectura + `ubigeos`, por slug. */
export const CATALOG_CONFIGS: Record<string, ResourceConfig> = {
  regions: readOnlyCatalog("regions", "Regiones", "región"),
  // CRUD (backend lo promovió a ENTITY_VIEWSETS: escritura `Administrador RENADS` + auditoría).
  "health-geographic-scopes": writableCatalog(
    "health-geographic-scopes",
    "Ámbitos geográficos sanitarios",
    "ámbito geográfico sanitario",
  ),
  "convention-types": readOnlyCatalog(
    "convention-types",
    "Tipos de convenio",
    "tipo de convenio",
  ),
  "convention-statuses": readOnlyCatalog(
    "convention-statuses",
    "Estados de convenio",
    "estado de convenio",
  ),
  "university-management-types": readOnlyCatalog(
    "university-management-types",
    "Tipos de gestión universitaria",
    "tipo de gestión universitaria",
  ),
  "authorization-types": writableCatalog(
    "authorization-types",
    "Tipos de autorización",
    "tipo de autorización",
  ),
  "academic-levels": writableCatalog(
    "academic-levels",
    "Niveles académicos",
    "nivel académico",
  ),
  specialties: readOnlyCatalog("specialties", "Especialidades", "especialidad"),
  "signing-authority-types": readOnlyCatalog(
    "signing-authority-types",
    "Tipos de autoridad firmante",
    "tipo de autoridad firmante",
  ),
  organs: {
    endpoint: "organs",
    title: "Categorías de órgano",
    singular: "categoría de órgano",
    readOnly: true,
    searchPlaceholder: "Buscar por nombre…",
    columns: [
      { key: "nombre", header: "Nombre" },
      { key: "estado", header: "Activo", render: (r: WithId) => siNo(r.estado) },
    ],
    filters: [{ name: "estado", label: "Activo", type: "boolean" }],
    fields: [],
  },
  "executive-positions": {
    endpoint: "executive-positions",
    title: "Cargos ejecutivos",
    singular: "cargo ejecutivo",
    writeRoles: ["Administrador RENADS"],
    searchPlaceholder: "Buscar por nombre del cargo…",
    columns: [
      {
        key: "organo_directivo_detalle",
        header: "Órgano del directorio",
        render: (r: WithId) => detalleNombre(r.organo_directivo_detalle),
      },
      { key: "nombre_masculino", header: "Nombre (masculino)" },
      { key: "nombre_femenino", header: "Nombre (femenino)" },
      { key: "activo", header: "Activo", render: (r: WithId) => siNo(r.activo) },
    ],
    filters: [
      {
        name: "organo_directivo",
        label: "Órgano del directorio",
        type: "select",
        optionsEndpoint: "organ-directories",
      },
      activoFilter,
    ],
    fields: [
      {
        name: "organo_directivo",
        label: "Órgano del directorio",
        type: "select",
        required: true,
        optionsEndpoint: "organ-directories",
      },
      { name: "nombre_masculino", label: "Nombre (masculino)", type: "text", required: true, uppercase: false },
      { name: "nombre_femenino", label: "Nombre (femenino)", type: "text", uppercase: false },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
  "observation-reasons": readOnlyCatalog(
    "observation-reasons",
    "Motivos de observación",
    "motivo de observación",
  ),
  "rejection-reasons": readOnlyCatalog(
    "rejection-reasons",
    "Motivos de rechazo",
    "motivo de rechazo",
  ),
  "closure-reasons": readOnlyCatalog(
    "closure-reasons",
    "Motivos de cierre",
    "motivo de cierre",
  ),
  categories: writableCatalog("categories", "Categorías", "categoría"),
  "classification-types": writableCatalog(
    "classification-types",
    "Tipos de clasificación",
    "tipo de clasificación",
  ),
  ubigeos: ubigeosConfig,
};

/** Orden y rótulos del índice de catálogos de solo lectura. */
export const CATALOG_MENU: { slug: string; title: string }[] = Object.entries(
  CATALOG_CONFIGS,
).map(([slug, config]) => ({ slug, title: config.title }));
