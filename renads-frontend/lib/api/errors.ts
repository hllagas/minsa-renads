import { AxiosError } from "axios";

/** Modelos del backend → nombre en español (plural) para mensajes de borrado protegido. */
const PROTECTED_MODEL_LABELS: Record<string, string> = {
  Student: "estudiantes",
  Tutor: "tutores",
  Internship: "internados",
  Internado: "internados",
  Rotation: "rotaciones",
  Activity: "actividades",
  Agreement: "convenios",
  Convenio: "convenios",
  Ipress: "IPRESS",
  ExecutingUnit: "unidades ejecutoras",
  RegionalOrgan: "órganos regionales",
  RegionalGovernment: "gobiernos regionales",
  Representative: "representantes",
};

/**
 * Extrae de la página de error de Django los modelos que bloquean el borrado (FK protegidas)
 * y arma un mensaje específico y accionable. Ej.: "...'Student.universidad'." → "estudiantes".
 */
function protectedDeleteMessage(html: string): string {
  const match = html.match(/protected foreign keys:\s*'([^']+)'/i);
  const labels = new Set<string>();
  if (match) {
    // Ej.: "Student.universidad, Rotation.internado" → ["Student", "Rotation"]
    for (const ref of match[1].split(",")) {
      const model = ref.trim().split(".")[0];
      labels.add(PROTECTED_MODEL_LABELS[model] ?? model.toLowerCase());
    }
  }
  if (labels.size) {
    return `No se puede eliminar: tiene ${[...labels].join(" y ")} asociados. Elimina o reasigna esos registros primero.`;
  }
  return "No se puede eliminar: el registro está referenciado por otros datos.";
}

/**
 * Convierte un error de Axios/DRF en un mensaje legible en español para el usuario.
 * DRF devuelve `{ detail }`, `{ non_field_errors: [...] }` o `{ campo: ["msg"] }`.
 */
export function extractApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    const data = error.response?.data;
    if (typeof data === "string") {
      // El backend puede devolver una página HTML de error (p. ej. 500 sin manejar).
      if (/^\s*</.test(data)) {
        if (/ProtectedError|protected foreign keys/i.test(data)) {
          return protectedDeleteMessage(data);
        }
        return "Error del servidor. Inténtalo de nuevo o contacta al administrador.";
      }
      return data;
    }
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
