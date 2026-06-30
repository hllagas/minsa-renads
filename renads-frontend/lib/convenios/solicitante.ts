import { api } from "@/lib/api/client";

/**
 * Entidad solicitante (relación polimórfica del convenio). El backend expone los `ContentType`
 * elegibles en `/solicitante-content-types/` (sus ids dependen de la base de datos). Aquí se
 * mapea cada `model` de Django al endpoint de su CRUD y a una etiqueta legible para la UI.
 */
export interface SolicitanteContentType {
  id: number;
  app_label: string;
  model: string;
}

/** `model` de Django → endpoint del CRUD + etiqueta legible del tipo de entidad. */
export const SOLICITANTE_ENTITIES: Record<string, { label: string; endpoint: string }> = {
  university: { label: "Universidad", endpoint: "universities" },
  ipress: { label: "IPRESS", endpoint: "ipress" },
  regionalgovernment: { label: "Gobierno Regional", endpoint: "regional-governments" },
  executingunit: { label: "Unidad Ejecutora", endpoint: "executing-units" },
  regionalorgan: { label: "Órgano Regional", endpoint: "regional-organs" },
  minsaorgan: { label: "Órgano MINSA", endpoint: "minsa-organs" },
  conapres: { label: "CONAPRES", endpoint: "conapres" },
};

/** Lista los tipos de entidad solicitante elegibles (con su `ContentType.id`). */
export async function listSolicitanteTypes(): Promise<SolicitanteContentType[]> {
  const { data } = await api.get<SolicitanteContentType[]>("/solicitante-content-types/");
  return data;
}
