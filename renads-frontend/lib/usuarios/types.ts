import type { WithId } from "@/lib/api/query";

/**
 * Tipos del módulo de Gestión de Usuarios (`apps/common`). Claves del API sin traducir.
 * Las contraseñas son **write-only**: jamás aparecen en los tipos de lectura.
 * Contrato: `docs/api-usuarios.md`.
 *
 * Los tipos de lectura extienden `WithId` (incluye la firma de índice que exige `ResourceConfig`).
 */

/** Rol/grupo resumido embebido en un usuario (`groups_detalle`). */
export interface GroupBrief {
  id: number;
  name: string;
}

/** Permiso resumido embebido en un rol (`permissions_detalle`). */
export interface PermissionBrief {
  id: number;
  name: string;
  codename: string;
  content_type: number;
  app_label: string;
  model: string;
}

/**
 * Ficha de usuario — lectura anidada bajo `perfil` (`UserProfileReadSerializer`, `apps/common`).
 * OJO por asimetría del backend: en LECTURA la ficha viene anidada; en ESCRITURA los campos van
 * PLANOS al nivel superior del payload (ver `UserCreatePayload`/`UserUpdatePayload`).
 * `unidad_organica_detalle`/`cargo_detalle` son STRINGS (`str(obj.*)`), no objetos `{id,nombre}`.
 */
export interface UserFichaRead {
  tipo_documento: string;
  numero_documento: string;
  apellido_paterno: string;
  apellido_materno: string;
  telefono: string;
  unidad_organica: number;
  cargo: number;
  tiene_ficha_usuario: boolean;
  unidad_organica_detalle: string;
  cargo_detalle: string;
}

/**
 * Usuario — lectura (`GET /users/`). Todos read-only; `password` nunca se devuelve.
 * La ficha de usuario (`apps/common`, endurecida) viene ANIDADA bajo `perfil` (o `null` si el
 * usuario aún no tiene `UserProfile`). La escritura, en cambio, es plana (ver payloads).
 */
export interface User extends WithId {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: string;
  last_login: string | null;
  groups: number[];
  groups_detalle: GroupBrief[];
  perfil: UserFichaRead | null;
}

/**
 * Usuario — alta (`POST /users/`). Incluye `password` write-only.
 * Los 7 campos de la ficha son **obligatorios** (el backend responde 400 si faltan);
 * `tiene_ficha_usuario` es opcional (default false).
 */
export interface UserCreatePayload {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  groups: number[];
  // Ficha de usuario (obligatoria en el alta).
  tipo_documento: string;
  numero_documento: string;
  apellido_paterno: string;
  apellido_materno: string;
  telefono: string;
  unidad_organica: number;
  cargo: number;
  tiene_ficha_usuario?: boolean;
}

/**
 * Usuario — edición (`PATCH /users/{id}/`). Igual que el alta pero **sin** `password`.
 * En PATCH los campos de ficha son opcionales, pero el `UserUpdateSerializer` usa
 * `allow_blank=False`/`allow_null=False`: NO deben enviarse vacíos ni nulos (el
 * `ResourceForm` omite del payload los opcionales vacíos, evitando el 400 — ver R7 del spec).
 */
export type UserUpdatePayload = Omit<UserCreatePayload, "password">;

/** Cambio de contraseña vía la acción `set-password`. */
export interface SetPasswordPayload {
  password: string;
}

/** Rol/Grupo — lectura/escritura (`groups`). `permissions_detalle` es read-only. */
export interface Group extends WithId {
  id: number;
  name: string;
  permissions: number[];
  permissions_detalle: PermissionBrief[];
}

/** Permiso — lectura (`permissions`, solo lectura). */
export interface Permission extends WithId {
  id: number;
  name: string;
  codename: string;
  content_type: number;
  app_label: string;
  model: string;
}

/**
 * Perfil institucional — lectura (`user-entity-profiles`). Polimórfico: `tipo_contenido`
 * (ContentType) + `id_objeto`. El backend devuelve ids crudos (sin `*_detalle`). Ver R-Q1.
 */
export interface UserEntityProfile extends WithId {
  id: number;
  usuario: number;
  tipo_contenido: number;
  id_objeto: number;
  grupo: number;
  activo: boolean;
}

/**
 * Perfil (alcance por objeto) — lectura del sub-recurso `users/{id}/profiles/` (backend T10).
 * A diferencia de `UserEntityProfile`, expone etiquetas legibles (`tipo_entidad`, `entidad`, `rol`)
 * además del `id_objeto` crudo. Mismo vocabulario que `GET /auth/me/` (`docs/api_accesos_frontend.md`).
 */
export interface UserProfileRead {
  id: number;
  tipo_entidad: string;
  id_objeto: number;
  entidad: string;
  rol: string;
  activo: boolean;
}

/**
 * Tipo de entidad asignable a un perfil (`GET /profile-entity-types/`, backend T11).
 * `tipo_entidad` es el `model` de Django en minúscula (el string que consume el POST de perfiles).
 */
export interface AssignableEntityType {
  id: number;
  tipo_entidad: string;
  label: string;
  app_label: string;
}

/** Payload de asignación (`POST /users/{id}/profiles/`): rol + tipo + ids de las entidades.
 * `ids` acepta PK numérica o textual (ipress `codigo_renipress`, executing-units `codigo`). */
export interface AssignProfilesPayload {
  rol: number;
  tipo_entidad: string;
  ids: (string | number)[];
}
