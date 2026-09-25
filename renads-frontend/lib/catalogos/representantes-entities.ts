import { api } from "@/lib/api/client";
import { ORGAN_NOMBRE } from "@/lib/catalogos/organs";

/**
 * Entidad de un representante/autoridad (relación polimórfica `entidad`). El backend expone los
 * `ContentType` elegibles en `/representante-content-types/` (ids dependientes de la BD). Como
 * MINSA/GORE/DIRIS son el mismo modelo `OrganicUnit` (discriminado por `organo`), la UI
 * ofrece 7 opciones pero solo hay 5 ContentTypes; los tres de OrganicUnit comparten id.
 */
export interface RepresentanteContentType {
  id: number;
  app_label: string;
  model: string;
}

/** Opción de «tipo de entidad» del paso 1 de la pantalla de representantes. */
export interface RepresentanteEntityOption {
  /** Clave estable de UI (única entre las 7 opciones). */
  key: string;
  /** Etiqueta legible. */
  label: string;
  /** `model` de Django (para resolver el `ContentType.id`). */
  model: string;
  /** Endpoint del CRUD de la entidad concreta (paso 2). */
  endpoint: string;
  /**
   * Para los tipos de OrganicUnit (MINSA/GORE/DIRIS): `nombre` del `Organ` por el que se filtra
   * la entidad concreta. La pantalla resuelve su id (vía `organs`) y pasa `?organo=<id>` — nunca
   * hardcodea el id ni usa `?categoria=`.
   */
  organoNombre?: string;
  /** `true` si la entidad es una OrganicUnit (habilita cargos por órgano). */
  esOrganicUnit: boolean;
}

/** Las 7 opciones de UI (5 ContentTypes; OrganicUnit se divide por `organo`). */
export const REPRESENTANTE_ENTITIES: RepresentanteEntityOption[] = [
  {
    key: "organo-minsa",
    label: "Órgano del MINSA",
    model: "organicunit",
    endpoint: "organic-units",
    organoNombre: ORGAN_NOMBRE.MINSA,
    esOrganicUnit: true,
  },
  {
    key: "gobierno-regional",
    label: "Gobierno Regional",
    model: "organicunit",
    endpoint: "organic-units",
    organoNombre: ORGAN_NOMBRE.GORE,
    esOrganicUnit: true,
  },
  {
    key: "diris",
    label: "DIRIS",
    model: "organicunit",
    endpoint: "organic-units",
    organoNombre: ORGAN_NOMBRE.DIRIS,
    esOrganicUnit: true,
  },
  {
    key: "universidad",
    label: "Universidad",
    model: "university",
    endpoint: "universities",
    esOrganicUnit: false,
  },
  {
    key: "unidad-ejecutora",
    label: "Unidad Ejecutora",
    model: "executingunit",
    endpoint: "executing-units",
    esOrganicUnit: false,
  },
  {
    key: "conapres",
    label: "CONAPRES",
    model: "conapres",
    endpoint: "conapres",
    esOrganicUnit: false,
  },
  {
    key: "ipress",
    label: "IPRESS",
    model: "ipress",
    endpoint: "ipress",
    esOrganicUnit: false,
  },
];

/** Busca la opción por su `key`. */
export function findEntityOption(key: string): RepresentanteEntityOption | undefined {
  return REPRESENTANTE_ENTITIES.find((o) => o.key === key);
}

/** Resuelve el `ContentType.id` de un `model` a partir de la respuesta del endpoint. */
export function resolveTipoContenidoId(
  model: string,
  types: RepresentanteContentType[] | undefined,
): number | undefined {
  return types?.find((t) => t.model === model)?.id;
}

/** Lista los tipos de entidad de representante elegibles (con su `ContentType.id`). */
export async function listRepresentanteTypes(): Promise<RepresentanteContentType[]> {
  const { data } = await api.get<RepresentanteContentType[]>(
    "/representante-content-types/",
  );
  return data;
}
