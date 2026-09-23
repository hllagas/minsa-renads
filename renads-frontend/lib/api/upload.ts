import type { AxiosResponse } from "axios";

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

/**
 * POST `multipart/form-data` cuya respuesta puede ser JSON o un archivo binario (p. ej. la
 * trama `.xlsx` anotada con las celdas inconsistentes). Devuelve la respuesta completa con el
 * cuerpo como `Blob` para inspeccionar `Content-Type` / cabeceras. No lanza en 422 (la carga
 * masiva devuelve el archivo anotado con ese estado).
 */
export async function postMultipartBlob(
  path: string,
  form: FormData,
): Promise<AxiosResponse<Blob>> {
  return api.post<Blob>(`/${path}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    responseType: "blob",
    validateStatus: (s) => (s >= 200 && s < 300) || s === 422,
  });
}
