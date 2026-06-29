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

/** Usuario — lectura (`GET /users/`). Todos read-only; `password` nunca se devuelve. */
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
}

/** Usuario — alta (`POST /users/`). Incluye `password` write-only. */
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
}

/** Usuario — edición (`PATCH /users/{id}/`). Igual que el alta pero **sin** `password`. */
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
