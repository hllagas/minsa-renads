import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

import { useAuthStore } from "@/lib/auth/store";

/** Base URL del backend RENADS. Dev: http://localhost:8000/api/v1 (ver docs/backend-overview.md). */
const baseURL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** Forma paginada estándar de DRF (PageNumberPagination). */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Cliente Axios único del proyecto. Solo debe usarse dentro de `lib/api/`. */
export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// --- Request: inyecta el access token ---
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

// --- Response: refresca el access en 401 y reintenta una vez ---
interface RetriableConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

// Evita ráfagas de refresh concurrentes: comparten la misma promesa.
let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const { refreshToken, setAccessToken, clear } = useAuthStore.getState();
  if (!refreshToken) {
    clear();
    throw new Error("No hay refresh token disponible.");
  }
  try {
    // Instancia limpia (sin interceptores) para no recursar en el 401.
    const { data } = await axios.post<{ access: string; refresh?: string }>(
      `${baseURL}/auth/token/refresh/`,
      { refresh: refreshToken },
    );
    setAccessToken(data.access);
    if (data.refresh) {
      useAuthStore.getState().setTokens(data.access, data.refresh);
    }
    return data.access;
  } catch (error) {
    clear();
    throw error;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const isAuthRoute = original?.url?.includes("/auth/token");

    if (error.response?.status === 401 && original && !original._retry && !isAuthRoute) {
      original._retry = true;
      try {
        refreshPromise = refreshPromise ?? refreshAccessToken();
        const newAccess = await refreshPromise;
        refreshPromise = null;
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>).Authorization = `Bearer ${newAccess}`;
        return api(original);
      } catch (refreshError) {
        refreshPromise = null;
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);
