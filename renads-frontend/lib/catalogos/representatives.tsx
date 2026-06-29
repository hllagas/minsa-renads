import type { ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

const siNo = (v: unknown) => (v ? "Sí" : "No");

/** Representante (polimórfico) tal como lo devuelve el backend (`representatives`). */
export interface Representante extends WithId {
  id: number;
  tipo_contenido: number;
  tipo_contenido_label?: string | null;
  id_objeto: number;
  nombre: string;
  cargo_ejecutivo: number;
  cargo_ejecutivo_nombre?: string | null;
  origen?: string | null;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
  activo: boolean;
}

/** Etiqueta legible de la entidad polimórfica destino. */
const entidadLabel = (r: Representante) =>
  `${r.tipo_contenido_label ?? `Tipo ${r.tipo_contenido}`} · #${r.id_objeto}`;

const ORIGEN_CHOICES = [
  { value: "MINSA", label: "MINSA" },
  { value: "GOBIERNO_REGIONAL", label: "Gobierno regional" },
  { value: "ASOCIACION_FACULTADES", label: "Asociación de facultades" },
];

/**
 * Config CRUD de `representatives` (v1, según `spec/catalogos.md` §5/R2):
 * list + filtros + editar (solo campos NO polimórficos) + eliminar. El ALTA queda diferida a v2
 * (requiere resolver `tipo_contenido`/`id_objeto` vía el endpoint `content-types`).
 */
export const REPRESENTATIVES_CONFIG: ResourceConfig<Representante> = {
  endpoint: "representatives",
  title: "Representantes",
  singular: "representante",
  description:
    "Representantes de órganos MINSA, órganos regionales, unidades ejecutoras, IPRESS y CONAPRES.",
  searchPlaceholder: "Buscar…",
  // TODO(v2 content-types): habilitar el ALTA con selector de tipo_contenido + combobox de id_objeto
  // dependiente, cuando el backend exponga el endpoint de solo lectura `content-types`.
  disableCreate: true,
  columns: [
    { key: "nombre", header: "Nombre" },
    {
      key: "cargo_ejecutivo",
      header: "Cargo ejecutivo",
      render: (r) => r.cargo_ejecutivo_nombre ?? `#${r.cargo_ejecutivo}`,
    },
    { key: "entidad", header: "Entidad", render: (r) => entidadLabel(r) },
    { key: "origen", header: "Origen", render: (r) => r.origen ?? "—" },
    { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
  ],
  filters: [
    {
      name: "tipo_contenido",
      label: "Tipo de contenido (ID)",
      type: "text",
      placeholder: "ID de ContentType",
    },
    { name: "id_objeto", label: "ID de objeto", type: "text", placeholder: "ID" },
    {
      name: "cargo_ejecutivo",
      label: "Cargo ejecutivo",
      type: "select",
      optionsEndpoint: "executive-positions",
    },
    { name: "activo", label: "Activo", type: "boolean" },
  ],
  // Solo campos NO polimórficos (PATCH parcial; no toca tipo_contenido/id_objeto).
  fields: [
    { name: "nombre", label: "Nombre", type: "text", required: true },
    {
      name: "cargo_ejecutivo",
      label: "Cargo ejecutivo",
      type: "select",
      required: true,
      optionsEndpoint: "executive-positions",
    },
    {
      name: "origen",
      label: "Origen (solo CONAPRES)",
      type: "select",
      choices: ORIGEN_CHOICES,
    },
    { name: "fecha_inicio", label: "Fecha de inicio", type: "date" },
    { name: "fecha_fin", label: "Fecha de fin", type: "date" },
    { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
  ],
  // La entidad polimórfica se muestra en solo lectura al editar (no es editable en v1).
  renderEditInfo: (r) => (
    <div className="grid gap-1">
      <span className="text-xs text-muted-foreground">Entidad (solo lectura)</span>
      <span className="font-medium">{entidadLabel(r)}</span>
    </div>
  ),
};
