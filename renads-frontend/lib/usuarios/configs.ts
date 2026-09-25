import type { FieldConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import type {
  Group,
  Permission,
  User,
  UserEntityProfile,
} from "@/lib/usuarios/types";

const siNo = (v: unknown) => (v ? "Sí" : "No");

/** Nombre completo a partir de `first_name` + `last_name`. */
const nombreCompleto = (r: User) =>
  [r.first_name, r.last_name].filter(Boolean).join(" ") || "—";

/** Etiqueta de un grupo/rol (FK `groups`): por nombre. */
const groupLabel = (r: WithId) => String(r.name ?? r.id);

/**
 * Choices estáticos del tipo de documento de la ficha de usuario. Conjunto cerrado ⇒ hardcode
 * (patrón `sexo` de `lib/internados/persons.ts`). Las claves replican `DOCUMENT_TYPE_CHOICES`
 * del backend (`apps/common`); un cambio de choices allí exige tocar esta lista.
 */
const TIPO_DOCUMENTO_CHOICES = [
  { value: "DNI", label: "DNI" },
  { value: "CE", label: "Carné de extranjería" },
  { value: "PASAPORTE", label: "Pasaporte" },
  { value: "RUC", label: "RUC" },
];

/** Etiqueta legible de un cargo (`executive-positions`): usa `nombre_masculino`/`nombre_femenino`. */
const cargoLabel = (r: WithId) =>
  String(r.nombre_masculino ?? r.nombre_femenino ?? r.id);

/**
 * Campos de la ficha de usuario (endurecida). El backend exige los 7 en el alta; en edición son
 * opcionales pero `allow_blank/allow_null=False`. `required` se pasa por parámetro para reutilizar
 * la misma definición en `createFields` (obligatorios) y `editFields` (opcionales; el `ResourceForm`
 * omite del payload los opcionales vacíos, evitando el 400 — ver R7 del spec).
 */
const fichaUsuarioFields = (required: boolean): FieldConfig[] => [
  { name: "_ficha", label: "Ficha de usuario", type: "separator" },
  {
    name: "tipo_documento",
    label: "Tipo de documento",
    type: "select",
    required,
    choices: TIPO_DOCUMENTO_CHOICES,
  },
  { name: "numero_documento", label: "Número de documento", type: "text", required, uppercase: false },
  { name: "apellido_paterno", label: "Apellido paterno", type: "text", required, uppercase: true },
  { name: "apellido_materno", label: "Apellido materno", type: "text", required, uppercase: true },
  { name: "telefono", label: "Teléfono", type: "text", required, uppercase: false },
  {
    name: "unidad_organica",
    label: "Unidad orgánica",
    type: "select",
    required,
    optionsEndpoint: "organic-units",
  },
  {
    name: "cargo",
    label: "Cargo",
    type: "select",
    required,
    optionsEndpoint: "executive-positions",
    optionsToLabel: cargoLabel,
  },
  { name: "tiene_ficha_usuario", label: "Tiene ficha de usuario", type: "boolean" },
];

/** Etiqueta de un permiso (FK `permissions`): `nombre (app_label.codename)`. */
const permissionLabel = (r: WithId) => {
  const app = r.app_label ? `${r.app_label}.${r.codename}` : r.codename;
  return r.name ? `${r.name} (${app})` : String(app ?? r.id);
};

/** Fecha legible (locale es-PE); vacío → «Nunca». */
const fechaHora = (v: unknown) =>
  v ? new Date(String(v)).toLocaleString("es-PE") : "Nunca";

/**
 * Usuarios (`users`) — CRUD. `DELETE` desactiva (baja lógica). Alta incluye `password` (write-only);
 * la edición no. Escritura solo superusuario (`requireSuperuser`). Acción `set-password` aparte.
 */
export const usersConfig: ResourceConfig<User> = {
  endpoint: "users",
  title: "Cuentas de usuario",
  singular: "usuario",
  description: "Administración de cuentas, estados y roles asignados.",
  searchPlaceholder: "Buscar por usuario, correo o nombre…",
  defaultOrdering: "id",
  requireSuperuser: true,
  softDelete: true,
  deleteActionLabel: "Desactivar",
  deleteSuccessMessage: "Usuario desactivado.",
  deleteConfirmDescription:
    "Esta acción desactiva la cuenta (no la elimina); podrá reactivarse editándola. ¿Deseas continuar?",
  // La ficha viene anidada bajo `perfil` en lectura, pero el form la escribe plana: aplánala al
  // nivel superior para que los 7 campos + `tiene_ficha_usuario` pre-rellenen la edición (H1).
  mapEditingToInitial: (row) => ({ ...row, ...(row.perfil ?? {}) }),
  columns: [
    { key: "username", header: "Usuario" },
    { key: "email", header: "Correo" },
    { key: "nombre", header: "Nombre", render: (r) => nombreCompleto(r) },
    {
      key: "numero_documento",
      header: "N.º documento",
      render: (r) => r.perfil?.numero_documento || "—",
    },
    {
      key: "unidad_organica_detalle",
      header: "Unidad orgánica",
      render: (r) => r.perfil?.unidad_organica_detalle || "—",
    },
    { key: "ficha", header: "Ficha", render: (r) => siNo(r.perfil?.tiene_ficha_usuario) },
    { key: "is_active", header: "Activo", render: (r) => siNo(r.is_active) },
    {
      key: "is_superuser",
      header: "Superusuario",
      render: (r) => siNo(r.is_superuser),
    },
    {
      key: "groups_detalle",
      header: "Roles",
      render: (r) =>
        r.groups_detalle?.map((g) => g.name).join(", ") || "—",
    },
    {
      key: "last_login",
      header: "Último acceso",
      render: (r) => fechaHora(r.last_login),
    },
  ],
  filters: [
    { name: "is_active", label: "Activo", type: "boolean" },
    { name: "is_superuser", label: "Superusuario", type: "boolean" },
    { name: "is_staff", label: "Staff", type: "boolean" },
    {
      name: "groups",
      label: "Rol",
      type: "select",
      optionsEndpoint: "groups",
      optionsToLabel: groupLabel,
    },
  ],
  // Alta: incluye `password` write-only + los 7 campos de ficha obligatorios (backend endurecido).
  createFields: [
    { name: "_cuenta", label: "Cuenta", type: "separator" },
    { name: "username", label: "Usuario", type: "text", required: true, uppercase: false },
    { name: "email", label: "Correo", type: "email", required: true },
    { name: "first_name", label: "Nombres", type: "text", uppercase: false },
    { name: "last_name", label: "Apellidos", type: "text", uppercase: false },
    { name: "password", label: "Contraseña", type: "password", required: true },
    { name: "is_active", label: "Activo", type: "boolean", defaultValue: true },
    { name: "is_staff", label: "Staff", type: "boolean" },
    { name: "is_superuser", label: "Superusuario", type: "boolean" },
    ...fichaUsuarioFields(true),
    { name: "_roles", label: "Roles", type: "separator" },
    {
      name: "groups",
      label: "Roles",
      type: "multiselect",
      optionsEndpoint: "groups",
      optionsToLabel: groupLabel,
    },
  ],
  // Edición: igual que el alta pero SIN `password` (se cambia con la acción `set-password`).
  // Los campos de ficha son opcionales aquí (`allow_blank/allow_null=False` en el backend); el
  // `ResourceForm` omite del payload los opcionales vacíos, así que un PATCH que no toca la ficha
  // no la degrada ni produce 400 (ver R7 del spec).
  editFields: [
    { name: "_cuenta", label: "Cuenta", type: "separator" },
    { name: "username", label: "Usuario", type: "text", required: true, uppercase: false },
    { name: "email", label: "Correo", type: "email", required: true },
    { name: "first_name", label: "Nombres", type: "text", uppercase: false },
    { name: "last_name", label: "Apellidos", type: "text", uppercase: false },
    { name: "is_active", label: "Activo", type: "boolean", defaultValue: true },
    { name: "is_staff", label: "Staff", type: "boolean" },
    { name: "is_superuser", label: "Superusuario", type: "boolean" },
    ...fichaUsuarioFields(false),
    { name: "_roles", label: "Roles", type: "separator" },
    {
      name: "groups",
      label: "Roles",
      type: "multiselect",
      optionsEndpoint: "groups",
      optionsToLabel: groupLabel,
    },
  ],
  // `fields` es el fallback; aquí no se usa porque hay create/editFields.
  fields: [],
};

/**
 * Roles / Grupos (`groups`) — CRUD. `name` + asignación múltiple de `permissions` (por ids).
 * Escritura solo superusuario.
 */
export const groupsConfig: ResourceConfig<Group> = {
  endpoint: "groups",
  title: "Roles",
  singular: "rol",
  description: "Roles del sistema y los permisos que agrupan.",
  searchPlaceholder: "Buscar por nombre…",
  defaultOrdering: "name",
  requireSuperuser: true,
  columns: [
    { key: "name", header: "Nombre" },
    {
      key: "permissions_detalle",
      header: "N.º de permisos",
      render: (r) => String(r.permissions_detalle?.length ?? 0),
    },
  ],
  fields: [
    { name: "name", label: "Nombre", type: "text", required: true, uppercase: false },
    {
      name: "permissions",
      label: "Permisos",
      type: "multiselect",
      optionsEndpoint: "permissions",
      optionsToLabel: permissionLabel,
    },
  ],
};

/**
 * Permisos (`permissions`) — solo lectura (catálogo de Django). Alimenta el selector de permisos
 * de un rol. Filtro `content_type__app_label` (texto) + search `name`/`codename`. Ordering `id`
 * (R-Q3): no se usa el ordering compuesto por `content_type`.
 */
export const permissionsConfig: ResourceConfig<Permission> = {
  endpoint: "permissions",
  title: "Permisos",
  singular: "permiso",
  description: "Catálogo de permisos de Django (solo lectura).",
  readOnly: true,
  searchPlaceholder: "Buscar por nombre o codename…",
  defaultOrdering: "id",
  columns: [
    { key: "name", header: "Nombre" },
    { key: "codename", header: "Codename" },
    { key: "app_label", header: "Aplicación" },
    { key: "model", header: "Modelo" },
  ],
  filters: [
    {
      name: "content_type__app_label",
      label: "Aplicación",
      type: "text",
      placeholder: "p. ej. convenios",
    },
  ],
  fields: [],
};

/**
 * Perfiles institucionales (`user-entity-profiles`) — v1 parcial. List + filtros + editar solo
 * `activo` + eliminar. Polimórfico (`tipo_contenido` + `id_objeto`); el backend devuelve ids crudos.
 * Escritura `Administrador RENADS`. **Alta diferida** (`disableCreate`).
 * TODO(v2 content-types): habilitar el alta cuando exista el endpoint `content-types` para resolver
 * `tipo_contenido`; entonces añadir `createFields` con usuario/tipo_contenido/id_objeto/grupo/activo.
 */
export const userEntityProfilesConfig: ResourceConfig<UserEntityProfile> = {
  endpoint: "user-entity-profiles",
  title: "Perfiles institucionales",
  singular: "perfil institucional",
  description: "Vínculo usuario ↔ entidad (alcance) y rol.",
  searchPlaceholder: "Buscar…",
  defaultOrdering: "id",
  writeRoles: ["Administrador RENADS"],
  disableCreate: true,
  columns: [
    { key: "usuario", header: "Usuario (id)", render: (r) => String(r.usuario) },
    { key: "grupo", header: "Rol (id)", render: (r) => String(r.grupo) },
    {
      key: "entidad",
      header: "Entidad",
      render: (r) => `${r.tipo_contenido} / ${r.id_objeto}`,
    },
    { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
  ],
  filters: [
    {
      name: "usuario",
      label: "Usuario (id)",
      type: "text",
      placeholder: "ID de usuario",
    },
    {
      name: "grupo",
      label: "Rol",
      type: "select",
      optionsEndpoint: "groups",
      optionsToLabel: groupLabel,
    },
    { name: "activo", label: "Activo", type: "boolean" },
  ],
  // En v1 solo se edita `activo`; el vínculo polimórfico es de solo lectura.
  editFields: [{ name: "activo", label: "Activo", type: "boolean" }],
  fields: [],
};
