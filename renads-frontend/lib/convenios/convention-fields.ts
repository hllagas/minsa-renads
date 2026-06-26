import type { FieldConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

/**
 * Campos del formulario de convenio (ConventionWrite). `fecha_fin`, `estado_actual` y `creado_por`
 * los fija el backend → no se exponen.
 *
 * Nota: `solicitante` es polimórfico (ContentType + id). No hay endpoint de ContentTypes en el
 * contrato, por lo que se capturan como números (el backend valida). Un selector entidad/tipo
 * queda pendiente para un pase posterior.
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
  { name: "codigo", label: "Código", type: "text" },
  {
    name: "convenio_marco",
    label: "Convenio Marco (solo Específico)",
    type: "select",
    optionsEndpoint: "conventions",
    optionsToLabel: (row: WithId) => String(row.titulo ?? row.codigo ?? row.id),
  },
  {
    name: "solicitante_tipo_contenido",
    label: "Tipo de entidad solicitante (ContentType id)",
    type: "number",
    required: true,
  },
  {
    name: "solicitante_id_objeto",
    label: "Id de la entidad solicitante",
    type: "number",
    required: true,
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
 * Campos para edición (PATCH). Excluye `tipo_convenio`: el serializer de lectura devuelve su
 * nombre, no el id, por lo que no es pre-rellenable; el tipo no se cambia en edición.
 */
export const CONVENTION_EDIT_FIELDS: FieldConfig[] = CONVENTION_FIELDS.filter(
  (f) => f.name !== "tipo_convenio",
);
