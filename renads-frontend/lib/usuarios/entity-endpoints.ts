import type { WithId } from "@/lib/api/query";

/**
 * Mapa de los 8 tipos de entidad asignables (backend `ASSIGNABLE_PROFILE_MODELS` / T11) al
 * endpoint del catálogo del que se listan sus entidades y a su etiqueta legible. La clave es el
 * `tipo_entidad` (`model` de Django en minúscula) que devuelve `GET /profile-entity-types/` y que
 * consume `POST /users/{id}/profiles/`. Conjunto cerrado ⇒ mapa estático.
 */
export const ENTITY_ENDPOINTS: Record<
  string,
  { endpoint: string; toLabel: (r: WithId) => string; valueKey?: string }
> = {
  university: {
    endpoint: "universities",
    toLabel: (r) => String(r.nombre ?? r.siglas ?? r.id),
  },
  // PK textual (`codigo_renipress`) → el valor de la asignación es el código string.
  ipress: {
    endpoint: "ipress",
    toLabel: (r) => String(r.nombre ?? r.codigo_renipress ?? r.id),
    valueKey: "codigo_renipress",
  },
  regionalgovernment: {
    endpoint: "regional-governments",
    toLabel: (r) => String(r.nombre ?? r.id),
  },
  organdirectory: {
    endpoint: "organ-directories",
    toLabel: (r) => String(r.nombre ?? r.id),
  },
  // PK textual (`codigo`) → el valor de la asignación es el código string.
  executingunit: {
    endpoint: "executing-units",
    toLabel: (r) => String(r.nombre ?? r.codigo ?? r.id),
    valueKey: "codigo",
  },
  conapres: { endpoint: "conapres", toLabel: (r) => String(r.nombre ?? r.id) },
  student: {
    endpoint: "students",
    toLabel: (r) =>
      `${r.nombres ?? ""} ${r.apellido_paterno ?? ""} (${r.numero_documento ?? r.id})`.trim(),
  },
};
