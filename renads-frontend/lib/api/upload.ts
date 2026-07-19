import { api } from "@/lib/api/client";

/**
 * POST `multipart/form-data` usando el cliente Axios único (JWT + refresh). El cliente fija
 * `Content-Type: application/json` por defecto; aquí se sobrescribe por petición para que Axios
 * calcule el `boundary` a partir del `FormData`. Axios sigue viviendo solo en `lib/api/`.
 */
export async function postMultipart<T>(path: string, form: FormData): Promise<T> {
  const { data } = await api.post<T>(`/${path}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}
