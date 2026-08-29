import { useQuery } from "@tanstack/react-query";

import { api, type Paginated } from "@/lib/api/client";
import type { Permission } from "@/lib/usuarios/types";

/**
 * Utilidades para la matriz de permisos por rol (`groups`). Agrupa el catálogo de Django
 * `permissions` en Aplicación → Modelo → acciones estándar (add/change/delete/view) para
 * renderizar la rejilla de checkboxes. Los permisos que no encajan en las 4 acciones estándar
 * (permisos personalizados del backend) NO se muestran en la matriz pero se conservan al guardar.
 */

/** Acciones estándar de Django que forman las columnas de la matriz. */
export const PERMISSION_ACTIONS = ["add", "change", "delete", "view"] as const;
export type PermissionAction = (typeof PERMISSION_ACTIONS)[number];

/** Etiqueta visible de cada acción (columna). */
export const ACTION_LABELS: Record<PermissionAction, string> = {
  add: "Agregar",
  change: "Modificar",
  delete: "Eliminar",
  view: "Ver",
};

/**
 * Nombres legibles de las aplicaciones (Django `app_label`). Fallback: se capitaliza el `app_label`.
 * Mantener sincronizado con los módulos del backend.
 */
const APP_LABELS: Record<string, string> = {
  convenios: "Gestionar convenios",
  internados: "Registrar internados",
  actividades: "Registrar actividades",
  common: "Usuarios y accesos",
  auth: "Autenticación",
  admin: "Administración del sitio",
  contenttypes: "Tipos de contenido",
  sessions: "Sesiones",
};

/** Capitaliza la primera letra (fallback de etiquetas). */
function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export function appLabel(appLabel: string): string {
  return APP_LABELS[appLabel] ?? capitalize(appLabel);
}

export function modelLabel(model: string): string {
  return capitalize(model);
}

/** Un modelo con los ids de permiso de cada acción estándar disponible. */
export interface ModelPermissions {
  model: string;
  label: string;
  /** id de permiso por acción; ausente si el backend no expone esa acción para el modelo. */
  actions: Partial<Record<PermissionAction, number>>;
}

/** Un grupo de aplicación con sus modelos (ordenados por etiqueta). */
export interface AppPermissions {
  app: string;
  label: string;
  models: ModelPermissions[];
}

/** Resultado de agrupar el catálogo de permisos para la matriz. */
export interface PermissionMatrix {
  apps: AppPermissions[];
  /** Todos los ids de permiso que la matriz gestiona (acciones estándar). */
  managedIds: Set<number>;
}

/** Trae TODAS las páginas del catálogo `permissions` (solo lectura, cambia rara vez). */
async function fetchAllPermissions(): Promise<Permission[]> {
  const all: Permission[] = [];
  let page = 1;
  for (;;) {
    const { data } = await api.get<Paginated<Permission>>("/permissions/", {
      params: { ordering: "id", ...(page > 1 ? { page } : {}) },
    });
    all.push(...data.results);
    if (!data.next) break;
    page += 1;
  }
  return all;
}

/** Query con el catálogo completo de permisos, cacheado (staleTime alto). */
export function useAllPermissions() {
  return useQuery({
    queryKey: ["permissions", "all"],
    queryFn: fetchAllPermissions,
    staleTime: 5 * 60_000,
  });
}

/**
 * Agrupa el catálogo plano de permisos en Aplicación → Modelo → acciones estándar.
 * Solo se consideran acciones cuyo `codename` sea exactamente `${accion}_${model}` (las 4 de Django).
 */
export function buildPermissionMatrix(permissions: Permission[]): PermissionMatrix {
  const managedIds = new Set<number>();
  // app_label -> (model -> ModelPermissions)
  const appMap = new Map<string, Map<string, ModelPermissions>>();

  for (const perm of permissions) {
    const action = perm.codename.split("_")[0] as PermissionAction;
    const isStandard =
      (PERMISSION_ACTIONS as readonly string[]).includes(action) &&
      perm.codename === `${action}_${perm.model}`;
    if (!isStandard) continue;

    let models = appMap.get(perm.app_label);
    if (!models) {
      models = new Map<string, ModelPermissions>();
      appMap.set(perm.app_label, models);
    }
    let node = models.get(perm.model);
    if (!node) {
      node = { model: perm.model, label: modelLabel(perm.model), actions: {} };
      models.set(perm.model, node);
    }
    node.actions[action] = perm.id;
    managedIds.add(perm.id);
  }

  const apps: AppPermissions[] = Array.from(appMap.entries())
    .map(([app, models]) => ({
      app,
      label: appLabel(app),
      models: Array.from(models.values()).sort((a, b) =>
        a.label.localeCompare(b.label, "es"),
      ),
    }))
    .sort((a, b) => a.label.localeCompare(b.label, "es"));

  return { apps, managedIds };
}
