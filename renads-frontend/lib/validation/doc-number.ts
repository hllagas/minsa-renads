import type { WithId } from "@/lib/api/query";

/**
 * Reglas de longitud del número de documento por tipo (RN de identidad, Perú):
 * - **DNI** (Documento Nacional de Identidad): exactamente **8** dígitos.
 * - Cualquier otro tipo (Carné de Extranjería, Pasaporte, …): exactamente **9** dígitos.
 *
 * El tipo se identifica por el `codigo` del catálogo `identity-document-types` (DNI = "DNI").
 * Reutilizado por Estudiantes, Tutores y Representantes.
 */
export const DNI_CODIGO = "DNI";
export const DNI_LENGTH = 8;
export const OTHER_DOC_LENGTH = 9;

/** Longitud esperada del número de documento según el `codigo` del tipo (DNI → 8, otro → 9). */
export function docLengthByCodigo(codigo: string | null | undefined): number {
  return String(codigo ?? "").toUpperCase() === DNI_CODIGO ? DNI_LENGTH : OTHER_DOC_LENGTH;
}

/**
 * Valida el número de documento contra el `codigo` del tipo. Devuelve `true` si es válido o un
 * mensaje de error. No exige presencia (el `required` se valida por separado).
 */
export function validateDocNumber(
  value: unknown,
  codigo: string | null | undefined,
): string | true {
  const v = String(value ?? "").trim();
  if (v === "") return true;
  if (!/^\d+$/.test(v)) return "Solo se permiten dígitos.";
  const esperado = docLengthByCodigo(codigo);
  if (v.length === esperado) return true;
  const etiqueta = String(codigo ?? "").toUpperCase() === DNI_CODIGO ? " (DNI)" : "";
  return `Debe tener ${esperado} dígitos${etiqueta}.`;
}

/** Resuelve el `codigo` de un tipo de documento por su id, dado el catálogo cargado. */
export function docCodigoById(
  rows: WithId[] | undefined,
  id: number | string | null | undefined,
): string | null {
  if (id == null) return null;
  const row = rows?.find((r) => r.id === id);
  return row ? String(row.codigo ?? "") : null;
}
