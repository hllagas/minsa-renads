import { AxiosError } from "axios";

/**
 * Convierte un error de Axios/DRF en un mensaje legible en español para el usuario.
 * DRF devuelve `{ detail }`, `{ non_field_errors: [...] }` o `{ campo: ["msg"] }`.
 */
export function extractApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data;
    if (typeof data === "string") return data;
    if (data && typeof data === "object") {
      const obj = data as Record<string, unknown>;
      if (typeof obj.detail === "string") return obj.detail;
      const partes: string[] = [];
      for (const [campo, valor] of Object.entries(obj)) {
        const msg = Array.isArray(valor) ? valor.join(" ") : String(valor);
        partes.push(campo === "non_field_errors" ? msg : `${campo}: ${msg}`);
      }
      if (partes.length) return partes.join(" · ");
    }
    if (error.code === "ERR_NETWORK") return "No se pudo conectar con el servidor.";
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Ocurrió un error inesperado.";
}
