import { createElement } from "react";

import type { FieldConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { SolicitanteField } from "@/components/convenios/solicitante-field";

/**
 * Campos del formulario de convenio (ConventionWrite). `fecha_fin`, `estado_actual` y `creado_por`
 * los fija el backend → no se exponen.
 *
 * `solicitante` es polimórfico (ContentType + id): en el alta se captura con un control compuesto
 * (`SolicitanteField`) que liga el tipo de entidad y la entidad concreta. En la edición se mantienen
 * los campos numéricos (el serializer de lectura devuelve ids), pendiente de migrar al control.
 */
export const CONVENTION_FIELDS: FieldConfig[] = [
  {
    name: "tipo_convenio",
    label: "Tipo de convenio",
    type: "select",
    required: true,
    optionsEndpoint: "convention-types",
  },
  { name: "titulo", label: "Título", type: "text", required: true },
  { name: "codigo", label: "Nomenclatura", type: "text" },
  {
    name: "plantilla",
    label: "Plantilla",
    type: "select",
    optionsEndpoint: "convention-templates",
  },
  {
    name: "convenio_marco",
    label: "Convenio Marco (solo Específico)",
    type: "select",
    optionsEndpoint: "conventions",
    optionsToLabel: (row: WithId) => String(row.titulo ?? row.codigo ?? row.id),
  },
  {
    name: "solicitante_tipo_contenido",
    label: "Tipo de entidad solicitante",
    type: "number",
    required: true,
  },
  {
    name: "solicitante_id_objeto",
    label: "Id de la entidad solicitante",
    type: "number",
    required: true,
  },
  {
    name: "organo_regional",
    label: "Órgano regional",
    type: "select",
    required: true,
    optionsEndpoint: "regional-organs",
  },
  {
    name: "universidad",
    label: "Universidad",
    type: "select",
    required: true,
    optionsEndpoint: "universities",
    optionsToLabel: (row: WithId) => String(row.nombre ?? row.siglas ?? row.id),
  },
  { name: "fecha_solicitud", label: "Fecha de solicitud", type: "date", required: true },
  { name: "fecha_inicio", label: "Fecha de inicio", type: "date" },
  {
    name: "max_campos_clinicos",
    label: "Máximo de campos clínicos (solo Específico)",
    type: "number",
  },
];

/**
 * Campos del alta de convenio. La entidad solicitante usa el control compuesto `SolicitanteField`
 * (tipo + entidad como selects ligados). Se omite `fecha_inicio`: la fija el backend al aprobarse
 * el convenio, no en el alta.
 */
export const CONVENTION_CREATE_FIELDS: FieldConfig[] = [
  {
    name: "tipo_convenio",
    label: "Tipo de convenio",
    type: "select",
    required: true,
    optionsEndpoint: "convention-types",
  },
  { name: "titulo", label: "Título", type: "text", required: true },
  { name: "codigo", label: "Nomenclatura", type: "text" },
  {
    name: "convenio_marco",
    label: "Convenio Marco (solo Específico)",
    type: "select",
    optionsEndpoint: "conventions",
    optionsToLabel: (row: WithId) => String(row.titulo ?? row.codigo ?? row.id),
  },
  {
    name: "solicitante",
    label: "Entidad solicitante",
    type: "custom",
    required: true,
    payloadKeys: ["solicitante_tipo_contenido", "solicitante_id_objeto"],
    render: (control) => createElement(SolicitanteField, { control }),
  },
  { name: "fecha_solicitud", label: "Fecha de solicitud", type: "date", required: true },
  {
    name: "max_campos_clinicos",
    label: "Máximo de campos clínicos (solo Específico)",
    type: "number",
  },
];

/**
 * Campos para edición (PATCH). Excluye `tipo_convenio`: el serializer de lectura devuelve su
 * nombre, no el id, por lo que no es pre-rellenable; el tipo no se cambia en edición.
 */
export const CONVENTION_EDIT_FIELDS: FieldConfig[] = CONVENTION_FIELDS.filter(
  (f) => f.name !== "tipo_convenio",
);
