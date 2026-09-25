import type { ReactNode } from "react";
import type { Control } from "react-hook-form";

import type { WithId } from "@/lib/api/query";

export type FieldType =
  | "text"
  | "number"
  | "boolean"
  | "date"
  | "email"
  | "select"
  | "password"
  | "multiselect"
  | "custom"
  /** Separador visual con encabezado de sección. No genera payload; siempre ocupa ancho completo. */
  | "separator";

/** Valores del formulario declarativo (claves = `FieldConfig.name`). */
export type FormValues = Record<string, unknown>;

export interface FieldConfig {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  /** Para `type: "select"`/`"multiselect"`: endpoint DRF que provee las opciones (búsqueda server-side). */
  optionsEndpoint?: string;
  /** Filtros fijos para el endpoint de opciones (p. ej. `{ activo: "true" }`). */
  optionsParams?: Record<string, string>;
  /**
   * Para `type: "select"` con `optionsEndpoint`: calcula los `optionsParams` a partir de los valores
   * **en vivo** del formulario (selects dependientes en cascada). Tiene prioridad sobre
   * `optionsParams` estático si ambos existen. P. ej. filtrar `red` por el ámbito elegido.
   */
  optionsParamsFrom?: (values: Record<string, unknown>) => Record<string, string>;
  /**
   * Para `type: "select"`: calcula los `optionsParams` a partir de **otra entidad relacionada** que
   * hay que resolver por su id (fetch async), no de valores planos del form. P. ej. filtrar `ipress`
   * por la unidad ejecutora del `convenio` elegido: se observa el campo `field` (id), se pide su
   * detalle a `endpoint`, y `toParams` mapea ese detalle a los query params. Mientras no haya
   * entidad resuelta, el select queda deshabilitado. Combinar con `resetsOn: [field]`.
   */
  optionsParamsFromEntity?: {
    /** Campo del form a observar (contiene el id de la entidad relacionada). */
    field: string;
    /** Endpoint DRF de la entidad relacionada (se pide el detalle por id). */
    endpoint: string;
    /** Mapea el detalle de la entidad a los query params del select (o `undefined` si no aplica). */
    toParams: (entity: WithId) => Record<string, string> | undefined;
  };
  /**
   * Nombres de los campos padre; al cambiar cualquiera, este campo se resetea a su valor vacío
   * (para no dejar seleccionada una opción que ya no es válida tras cambiar el filtro padre).
   */
  resetsOn?: string[];
  /**
   * El campo se renderiza y valida en el formulario pero **se excluye del payload** enviado al
   * backend (campo auxiliar de UI, p. ej. el ámbito que filtra la red en el alta de microrred).
   */
  virtual?: boolean;
  /**
   * Condición de visibilidad dinámica. Recibe los valores actuales del formulario; si retorna
   * `false`, el campo se oculta (y no se incluye en el payload). P. ej. mostrar `content_types`
   * solo cuando `controla_acceso === true`.
   */
  showWhen?: (values: Record<string, unknown>) => boolean;
  /** Etiqueta de cada opción (por defecto `nombre`/`titulo`). */
  optionsToLabel?: (row: WithId) => string;
  /** Solo para `type: "select"`: opciones estáticas (enum). Si está, no usa endpoint. */
  choices?: { value: string; label: string }[];
  /**
   * Solo para `type: "select"` con `optionsEndpoint`: usa esta clave del registro como **valor**
   * (cadena) en vez del `id`. P. ej. `"codigo"` para enviar el código de estado y no su id.
   * Renderiza un dropdown (no búsqueda) con la etiqueta de `optionsToLabel`/`nombre`.
   */
  optionsValueKey?: string;
  /**
   * Solo con `optionsValueKey`: renderiza un `EntityCombobox` con búsqueda server-side (en vez del
   * `CodeSelect` de 1ª página) usando `optionsValueKey` como `valueKey`. Para FKs de **PK textual**
   * que pueden ser catálogos grandes (`executing-units.codigo`, `ipress.codigo_renipress`).
   */
  optionsSearchable?: boolean;
  /** Valor por defecto al crear. */
  defaultValue?: string | number | boolean | null;
  /**
   * Para `type: "text"`: fuerza el valor a MAYÚSCULAS (por defecto activo en texto).
   * Poner `false` para excluir (p. ej. `username`, que es sensible a may/min en el login).
   */
  uppercase?: boolean;
  /**
   * Para `type: "text"`: restringe la entrada a dígitos (0-9) únicamente. Útil para campos de
   * teléfono o código numérico que no deben aceptar letras ni símbolos.
   */
  numericOnly?: boolean;
  /** Para `type: "number"`: valor mínimo permitido (inclusive). */
  min?: number;
  /** Para `type: "number"`: valor máximo permitido (inclusive). */
  max?: number;
  /** Para `type: "number"`: máximo de decimales permitidos (p. ej. 3 → hasta 0.001). */
  decimals?: number;
  /** Deshabilita el campo (solo lectura en el formulario). */
  disabled?: boolean;
  /**
   * Para un campo de **número de documento** (`type: "text"`): nombre del select del **tipo de
   * documento** (`identity-document-types`). Valida la longitud según el tipo elegido: DNI → 8
   * dígitos, otro → 9 (solo dígitos). Ver `lib/validation/doc-number.ts`.
   */
  docNumberFor?: string;
  /**
   * Fuerza el campo a ocupar todo el ancho en el formulario de 2 columnas (p. ej. nombres largos,
   * direcciones, descripciones). Los tipos `custom`/`multiselect` ya ocupan todo el ancho.
   */
  fullWidth?: boolean;
  /**
   * Para `type: "custom"`: render propio del campo (recibe el `control` de react-hook-form).
   * El componente gestiona sus propios `Controller`/`useController`; útil para controles
   * compuestos como el selector polimórfico de entidad solicitante (tipo + entidad ligados).
   */
  render?: (control: Control<FormValues>) => ReactNode;
  /**
   * Para `type: "custom"`: claves que el campo aporta al payload (un control compuesto puede
   * escribir varias). Cada clave se serializa como número si tiene valor. Si se omite, se usa `name`.
   */
  payloadKeys?: string[];
}

export interface ColumnConfig<T extends WithId = WithId> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
}

/** Variantes de botón admitidas por las acciones por fila (subconjunto de `Button`). */
export type RowActionVariant =
  | "default"
  | "outline"
  | "secondary"
  | "destructive"
  | "ghost";

/**
 * Acción por fila inyectada por la página que monta `ResourceCrud` (no es data; vive en el
 * componente). El estado/diálogo asociado lo posee la página (p. ej. el diálogo de contraseña).
 */
export interface RowAction<TRead extends WithId = WithId> {
  key: string;
  label: string;
  variant?: RowActionVariant;
  /** Render personalizado del botón/control (si se omite, se usa un `Button` estándar). */
  render?: (row: TRead) => ReactNode;
  onClick: (row: TRead) => void;
  /** Condiciona la visibilidad de la acción para una fila concreta. */
  visible?: (row: TRead) => boolean;
}

/** Tipo de control de un filtro de listado declarativo. */
export type FilterType = "select" | "boolean" | "text";

/**
 * Filtro declarativo de un listado (mapea a los `filterset_fields` de django-filter del backend).
 * Reutiliza la forma de `FieldConfig` para los selects (FK por endpoint o enum por `choices`).
 */
export interface FilterConfig {
  /** Nombre exacto del query param del backend (p. ej. `universidad`, `activo`). */
  name: string;
  label: string;
  type: FilterType;
  /** Solo `type: "select"` sin `choices`: endpoint DRF que provee las opciones (FK). */
  optionsEndpoint?: string;
  /** Filtros fijos para el endpoint de opciones (p. ej. `{ activo: "true" }`). */
  optionsParams?: Record<string, string>;
  /** Etiqueta de cada opción del select FK. */
  optionsToLabel?: (row: WithId) => string;
  /** Solo `type: "select"`: opciones estáticas (enum). Si está, no usa endpoint. */
  choices?: { value: string; label: string }[];
  /** Placeholder para filtros de texto. */
  placeholder?: string;
  /** Clave del registro usada como valor del filtro (para FK de PK textual, p. ej. `"codigo"`). */
  optionsValueKey?: string;
  /** Con `optionsValueKey`: usa `EntityCombobox`+`valueKey` (búsqueda) en vez del select simple. */
  optionsSearchable?: boolean;
}

/** Configuración declarativa de un recurso CRUD (entidad maestra del backend). */
export interface ResourceConfig<TRead extends WithId = WithId> {
  /** Endpoint DRF, p. ej. `universities`. */
  endpoint: string;
  /**
   * Nombre del campo que es la **clave primaria** del recurso (default `"id"`). Para recursos con
   * PK textual usar `"codigo"` (executing-units) o `"codigo_renipress"` (ipress). Afecta al valor
   * usado para editar/eliminar/keyear filas y al ordering por defecto.
   */
  pkField?: string;
  /** Título plural, p. ej. "Universidades". */
  title: string;
  /** Singular para diálogos, p. ej. "universidad". */
  singular: string;
  /** Prefijo del diálogo de alta (por defecto "Nuevo"; usar "Nueva" para entidades femeninas). */
  createPrefix?: string;
  description?: string;
  columns: ColumnConfig<TRead>[];
  /** Campos del formulario (fallback común para alta y edición). */
  fields: FieldConfig[];
  /** Campos solo para el alta (si se omite, se usa `fields`). P. ej. usuario con `password`. */
  createFields?: FieldConfig[];
  /** Campos solo para la edición (si se omite, se usa `fields`). P. ej. usuario sin `password`. */
  editFields?: FieldConfig[];
  searchPlaceholder?: string;
  /** Filtros declarativos (django-filter). Se aplican vía `ListParams.filters`. */
  filters?: FilterConfig[];
  /** Orden por defecto del listado (DRF `ordering`). Por defecto `id`. */
  defaultOrdering?: string;
  /** Roles con permiso de escritura (por defecto solo `Administrador RENADS`). */
  writeRoles?: string[];
  /** Solo lectura explícito: oculta toda acción de escritura para cualquier rol. */
  readOnly?: boolean;
  /** Oculta la acción "Nuevo" conservando editar/eliminar (p. ej. alta diferida a v2). */
  disableCreate?: boolean;
  /**
   * Exige superusuario (`es_superusuario`) además de `writeRoles` para escribir/crear.
   * El gating del front es UX; el backend (`IsSuperUser`) es la autoridad final.
   */
  requireSuperuser?: boolean;
  /** Clase CSS aplicada al contenedor raíz (p. ej. `max-w-2xl` para tablas con pocas columnas). */
  containerClassName?: string;
  /** Baja lógica: el `DELETE` desactiva el registro (no lo borra). Cambia copy de confirmación. */
  softDelete?: boolean;
  /** Etiqueta del botón de borrado (por defecto "Eliminar"; p. ej. "Desactivar"). */
  deleteActionLabel?: string;
  /** Título del diálogo de borrado (por defecto `${acción} ${singular}`). */
  deleteConfirmTitle?: string;
  /** Descripción del diálogo de borrado (sobrescribe el texto por defecto). */
  deleteConfirmDescription?: string;
  /** Mensaje de éxito tras borrar (por defecto `${singular} eliminada.`). */
  deleteSuccessMessage?: string;
  /**
   * Mapea la fila cruda de lectura al objeto `initial` del formulario de edición. Útil cuando la
   * respuesta de lectura anida campos que el form espera al nivel superior (p. ej. `users` devuelve
   * la ficha bajo `perfil`, pero el form la escribe plana). Si se omite, se usa la fila tal cual.
   */
  mapEditingToInitial?: (row: TRead) => Record<string, unknown>;
  /** Contenido de solo lectura mostrado encima del formulario al editar (no al crear). */
  renderEditInfo?: (row: TRead) => ReactNode;
  /** Clase del `DialogContent` de alta/edición (valor por defecto en `ResourceCrud`: `sm:max-w-2xl`). */
  dialogClassName?: string;
  /** Clase CSS del `<form>` en modo edición (sobrescribe la clase por defecto de `ResourceForm`). */
  editFormClassName?: string;
  /** Clase CSS del `<form>` en modo alta (sobrescribe la clase por defecto de `ResourceForm`). */
  createFormClassName?: string;
}
