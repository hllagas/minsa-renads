import type { FieldConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { boolIcon } from "@/components/ui/bool-icon";
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
 * Campos de la ficha de usuario (endurecida). El backend la exige solo a los no-superusuarios (valida
 * por rol); el formulario es **uniforme** para todos. Por eso la ficha va siempre con
 * `required:false` (sin bloqueo de cliente) + `requiredMark:true` (asterisco visual). El
 * `ResourceForm` omite del payload los opcionales vacíos, evitando el 400 por `allow_blank/allow_null`
 * en la edición parcial. Idéntica en alta y edición ⇒ sin parámetro (ver T10 del spec).
 */
const fichaUsuarioFields = (): FieldConfig[] => [
  {
    name: "tipo_documento",
    label: "Tipo de documento",
    type: "select",
    required: false,
    requiredMark: true,
    choices: TIPO_DOCUMENTO_CHOICES,
  },
  {
    name: "numero_documento",
    label: "Número de documento",
    type: "text",
    required: false,
    requiredMark: true,
    uppercase: false,
  },
  {
    name: "telefono",
    label: "Teléfono",
    type: "text",
    required: false,
    requiredMark: true,
    numericOnly: true,
    uppercase: false,
  },
  {
    name: "unidad_organica",
    label: "Unidad orgánica",
    type: "select",
    required: false,
    requiredMark: true,
    optionsEndpoint: "organic-units",
  },
  {
    name: "cargo",
    label: "Cargo",
    type: "select",
    required: false,
    requiredMark: true,
    optionsEndpoint: "executive-positions",
    optionsToLabel: cargoLabel,
    // Cascada: el cargo se filtra por la unidad orgánica elegida (`executive-positions?unidad_organica=<id>`).
    // Mientras no haya unidad seleccionada, no se pasa filtro (lista completa). Al cambiar la unidad, el
    // cargo se resetea para no dejar seleccionado uno que ya no pertenece a la nueva unidad.
    optionsParamsFrom: (v): Record<string, string> =>
      v.unidad_organica ? { unidad_organica: String(v.unidad_organica) } : {},
    resetsOn: ["unidad_organica"],
  },
];

/** Etiqueta de un permiso (FK `permissions`): `nombre (app_label.codename)`. */
const permissionLabel = (r: WithId) => {
  const app = r.app_label ? `${r.app_label}.${r.codename}` : r.codename;
  return r.name ? `${r.name} (${app})` : String(app ?? r.id);
};

/** Fecha legible (locale es-PE); vacío → «Nunca». */
const fechaHora = (v: unknown) =>
  v ? new Date(String(v)).toLocaleString("es-PE") : "Nunca";

// Ficha de usuario en el orden de la tabla §1: [tipo_documento, numero_documento, telefono,
// unidad_organica, cargo]. `email` se intercala aparte entre `numero_documento` y `telefono`.
const [
  fichaTipoDocumento,
  fichaNumeroDocumento,
  fichaTelefono,
  fichaUnidadOrganica,
  fichaCargo,
] = fichaUsuarioFields();

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
    { key: "ficha", header: "Ficha", render: (r) => boolIcon(Boolean(r.perfil?.tiene_ficha_usuario)) },
    { key: "is_active", header: "Activo", render: (r) => boolIcon(Boolean(r.is_active)) },
    {
      key: "is_superuser",
      header: "Superusuario",
      render: (r) => boolIcon(Boolean(r.is_superuser)),
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
  // Alta — formulario UNIFORME para todo rol (sin `showWhen`): los 15 campos en el orden fijo de la
  // tabla §1 del spec. La ficha y los nombres van con `requiredMark` (asterisco visual) pero
  // `required:false` (el cliente no bloquea; el backend valida por rol). `password` se autogenera y
  // prellena al montar (solo aquí). `email` sí es obligatorio (backend lo exige a todos).
  createFields: [
    // 1. `username` — editable en el alta (el super lo teclea; para no-super el backend lo genera del
    //    documento y es read-only). Helper explicativo bajo el input.
    {
      name: "username",
      label: "Usuario",
      type: "text",
      uppercase: false,
      required: false,
      helperText: "Para usuarios no-superadmin se genera del número de documento",
    },
    // 2. `password` — autogenerado + mostrar/ocultar + regenerar. Solo en el alta.
    {
      name: "password",
      label: "Contraseña",
      type: "password",
      required: true,
      autogenerate: true,
    },
    // 3-4. Nombres/Apellidos (auth_user) — asterisco visual, sin bloqueo de cliente.
    { name: "first_name", label: "Nombres", type: "text", uppercase: false, required: false, requiredMark: true },
    { name: "last_name", label: "Apellidos", type: "text", uppercase: false, required: false, requiredMark: true },
    // 5-6. Ficha: tipo/número de documento.
    fichaTipoDocumento,
    fichaNumeroDocumento,
    // 7. Correo — obligatorio para todos.
    { name: "email", label: "Correo", type: "email", required: true },
    // 8-10. Ficha: teléfono, unidad orgánica, cargo.
    fichaTelefono,
    fichaUnidadOrganica,
    fichaCargo,
    // 11-14. Flags de cuenta.
    { name: "tiene_ficha_usuario", label: "Tiene ficha de usuario", type: "boolean" },
    { name: "is_staff", label: "Staff", type: "boolean" },
    { name: "is_superuser", label: "Superusuario", type: "boolean" },
    { name: "is_active", label: "Activo", type: "boolean", defaultValue: true },
    // 15. Roles (ocupa ancho completo).
    {
      name: "groups",
      label: "Roles",
      type: "multiselect",
      optionsEndpoint: "groups",
      optionsToLabel: groupLabel,
    },
  ],
  // Edición — mismo orden 1,3..15 SIN `password` (el cambio va por la acción `set-password`).
  // `username` deshabilitado (read-only en el backend; enviarlo en PATCH es inocuo). La ficha va
  // `required:false`+`requiredMark`; el `ResourceForm` omite del payload los opcionales vacíos, así
  // que un PATCH que no toca la ficha no la degrada ni produce 400.
  editFields: [
    {
      name: "username",
      label: "Usuario",
      type: "text",
      uppercase: false,
      required: false,
      disabled: true,
      helperText: "No editable (se conserva del alta)",
    },
    { name: "first_name", label: "Nombres", type: "text", uppercase: false, required: false, requiredMark: true },
    { name: "last_name", label: "Apellidos", type: "text", uppercase: false, required: false, requiredMark: true },
    fichaTipoDocumento,
    fichaNumeroDocumento,
    { name: "email", label: "Correo", type: "email", required: true },
    fichaTelefono,
    fichaUnidadOrganica,
    fichaCargo,
    { name: "tiene_ficha_usuario", label: "Tiene ficha de usuario", type: "boolean" },
    { name: "is_staff", label: "Staff", type: "boolean" },
    { name: "is_superuser", label: "Superusuario", type: "boolean" },
    { name: "is_active", label: "Activo", type: "boolean", defaultValue: true },
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
