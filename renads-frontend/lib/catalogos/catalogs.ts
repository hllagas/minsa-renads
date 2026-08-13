import type { FilterConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

const siNo = (v: unknown) => (v ? "Sí" : "No");

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
      { name: "nombre", label: "Nombre", type: "text", required: true },
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
  "health-geographic-scopes": readOnlyCatalog(
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
  "document-types": writableCatalog(
    "document-types",
    "Tipos de documento",
    "tipo de documento",
  ),
  "university-management-types": readOnlyCatalog(
    "university-management-types",
    "Tipos de gestión universitaria",
    "tipo de gestión universitaria",
  ),
  "university-entity-types": writableCatalog(
    "university-entity-types",
    "Tipos de entidad universitaria",
    "tipo de entidad universitaria",
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
  "regional-organ-types": writableCatalog(
    "regional-organ-types",
    "Tipos de órgano regional",
    "tipo de órgano regional",
  ),
  "executing-unit-types": readOnlyCatalog(
    "executing-unit-types",
    "Tipos de unidad ejecutora",
    "tipo de unidad ejecutora",
  ),
  "minsa-organ-types": writableCatalog(
    "minsa-organ-types",
    "Tipos de órgano MINSA",
    "tipo de órgano MINSA",
  ),
  "executive-positions": readOnlyCatalog(
    "executive-positions",
    "Cargos ejecutivos",
    "cargo ejecutivo",
  ),
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
