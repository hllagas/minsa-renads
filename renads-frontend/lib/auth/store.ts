import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Perfil institucional del usuario (vínculo con una entidad concreta para el alcance).
 * Forma definida por el backend en `GET /auth/me/` (ver docs/api-auth.md).
 */
export interface UserProfile {
  tipo_entidad: string;
  id_objeto: number;
  entidad: string;
  rol: string;
}

/** Módulo (ContentType) gobernado por el calendario, tal como lo expone `/auth/me/`. */
export interface ModuleState {
  app_label: string;
  model: string;
  content_type_id: number;
}

/** Usuario autenticado tal como lo devuelve `GET /auth/me/`. */
export interface AuthUser {
  id: number;
  username: string;
  email: string;
  nombre: string;
  es_superusuario: boolean;
  grupos: string[];
  perfiles: UserProfile[];
  /** Contraseña temporal pendiente de cambio (RN-22). El front bloquea hasta cambiarla. */
  debe_cambiar_password?: boolean;
  /** Módulos con ventana de calendario vigente (escritura habilitada). */
  modulos_habilitados?: ModuleState[];
  /** Módulos gobernados pero fuera de ventana (escritura bloqueada, salvo admin/superusuario). */
  modulos_bloqueados?: ModuleState[];
}

export interface PendingTwoFactor {
  sessionToken: string;
  method: "TOTP" | "EMAIL";
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  /** Datos transitorios del flujo 2FA (no persistidos). */
  pendingTwoFactor: PendingTwoFactor | null;
  /** Guarda el par de tokens tras login/refresh. */
  setTokens: (access: string, refresh: string) => void;
  /** Actualiza solo el access (tras refresh). */
  setAccessToken: (access: string) => void;
  /** Guarda los datos del usuario (`/auth/me/`). */
  setUser: (user: AuthUser | null) => void;
  /** Guarda el estado transitorio de 2FA pendiente. */
  setPendingTwoFactor: (p: PendingTwoFactor | null) => void;
  /** Limpia la sesión (logout / refresh fallido). */
  clear: () => void;
}

/**
 * Estado de sesión (cliente). Solo guarda tokens y el usuario; los datos de servidor (listas,
 * detalles) viven en TanStack Query, no aquí. El access token también lo leen los interceptores
 * de Axios (lib/api/client.ts) vía `useAuthStore.getState()`.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      pendingTwoFactor: null,
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setAccessToken: (accessToken) => set({ accessToken }),
      setUser: (user) => set({ user }),
      setPendingTwoFactor: (pendingTwoFactor) => set({ pendingTwoFactor }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null, pendingTwoFactor: null }),
    }),
    {
      name: "renads-auth",
      // No persistir el usuario ni el estado 2FA transitorio.
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    },
  ),
);

/** Helpers de gating por rol (la autoridad final es el backend; esto es UX). */
export const userHasRole = (user: AuthUser | null, ...roles: string[]): boolean =>
  !!user && (user.es_superusuario || roles.some((r) => user.grupos.includes(r)));

/**
 * Gating estricto a superusuario puro (`es_superusuario`). Más restrictivo que `userHasRole`:
 * no basta con tener un grupo/rol. Lo exige `/usuarios` (cuentas/roles/permisos).
 */
export const isSuperuser = (user: AuthUser | null): boolean => !!user?.es_superusuario;

/**
 * Indica si un módulo (`app_label.model`) está fuera de su ventana de calendario para el usuario.
 * Refleja el estado temporal del backend (`modulos_bloqueados` de `/auth/me/`) para UX (deshabilitar
 * acciones de escritura). El admin/superusuario está exento del gate, pero el módulo puede seguir
 * apareciendo como bloqueado; por eso se combina con la exención. La autoridad final es el backend.
 */
export const moduloBloqueado = (
  user: AuthUser | null,
  appLabel: string,
  model: string,
): boolean => {
  if (!user || user.es_superusuario || user.grupos.includes("Administrador RENADS")) return false;
  return (user.modulos_bloqueados ?? []).some(
    (m) => m.app_label === appLabel && m.model === model,
  );
};
