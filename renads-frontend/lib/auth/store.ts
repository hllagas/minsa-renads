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

/** Usuario autenticado tal como lo devuelve `GET /auth/me/`. */
export interface AuthUser {
  id: number;
  username: string;
  email: string;
  nombre: string;
  es_superusuario: boolean;
  grupos: string[];
  perfiles: UserProfile[];
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  /** Guarda el par de tokens tras login/refresh. */
  setTokens: (access: string, refresh: string) => void;
  /** Actualiza solo el access (tras refresh). */
  setAccessToken: (access: string) => void;
  /** Guarda los datos del usuario (`/auth/me/`). */
  setUser: (user: AuthUser | null) => void;
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
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setAccessToken: (accessToken) => set({ accessToken }),
      setUser: (user) => set({ user }),
      clear: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: "renads-auth",
      // No persistir el usuario: se recarga desde /auth/me/ con Query al iniciar.
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
