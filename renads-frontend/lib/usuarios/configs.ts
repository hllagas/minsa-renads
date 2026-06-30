import type { ResourceConfig } from "@/lib/crud/types";
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
  columns: [
    { key: "username", header: "Usuario" },
    { key: "email", header: "Correo" },
    { key: "nombre", header: "Nombre", render: (r) => nombreCompleto(r) },
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
  // Alta: incluye `password` write-only.
  createFields: [
    { name: "username", label: "Usuario", type: "text", required: true, uppercase: false },
    { name: "email", label: "Correo", type: "email", required: true },
    { name: "first_name", label: "Nombres", type: "text" },
    { name: "last_name", label: "Apellidos", type: "text" },
    { name: "password", label: "Contraseña", type: "password", required: true },
    { name: "is_active", label: "Activo", type: "boolean", defaultValue: true },
    { name: "is_staff", label: "Staff", type: "boolean" },
    { name: "is_superuser", label: "Superusuario", type: "boolean" },
    {
      name: "groups",
      label: "Roles",
      type: "multiselect",
      optionsEndpoint: "groups",
      optionsToLabel: groupLabel,
    },
  ],
  // Edición: igual que el alta pero SIN `password` (se cambia con la acción `set-password`).
  editFields: [
    { name: "username", label: "Usuario", type: "text", required: true, uppercase: false },
    { name: "email", label: "Correo", type: "email", required: true },
    { name: "first_name", label: "Nombres", type: "text" },
    { name: "last_name", label: "Apellidos", type: "text" },
    { name: "is_active", label: "Activo", type: "boolean", defaultValue: true },
    { name: "is_staff", label: "Staff", type: "boolean" },
    { name: "is_superuser", label: "Superusuario", type: "boolean" },
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
    { name: "name", label: "Nombre", type: "text", required: true },
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
