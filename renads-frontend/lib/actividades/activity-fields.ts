import type { FieldConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

const personaLabel = (row: WithId) =>
  `${row.nombres ?? ""} ${row.apellido_paterno ?? ""} (${row.numero_documento ?? row.id})`.trim();
const internadoLabel = (row: WithId) => `${row.interno ?? "Internado"} (${row.convenio ?? row.id})`;
const rotacionLabel = (row: WithId) => `Rotación #${row.numero_rotacion ?? row.id}`;

/** Campos de alta de actividad (TeachingActivityWrite). `estado_actual`/`creado_por` los fija el backend. */
export const ACTIVITY_FIELDS: FieldConfig[] = [
  {
    name: "interno",
    label: "Interno",
    type: "select",
    required: true,
    optionsEndpoint: "interns",
    optionsToLabel: personaLabel,
  },
  {
    name: "internado",
    label: "Internado",
    type: "select",
    required: true,
    optionsEndpoint: "internships",
    optionsToLabel: internadoLabel,
  },
  { name: "ipress", label: "Sede docente (IPRESS)", type: "select", required: true, optionsEndpoint: "ipress" },
  {
    name: "rotacion",
    label: "Rotación (opcional)",
    type: "select",
    optionsEndpoint: "rotations",
    optionsToLabel: rotacionLabel,
  },
  {
    name: "tutor",
    label: "Tutor",
    type: "select",
    required: true,
    optionsEndpoint: "tutors",
    optionsToLabel: personaLabel,
  },
  {
    name: "servicio_area",
    label: "Servicio / área",
    type: "select",
    required: true,
    optionsEndpoint: "service-areas",
  },
  {
    name: "tipo_actividad",
    label: "Tipo de actividad",
    type: "select",
    required: true,
    optionsEndpoint: "activity-types",
  },
  { name: "fecha_actividad", label: "Fecha de actividad", type: "date", required: true },
  { name: "descripcion", label: "Descripción", type: "text" },
  { name: "carga_horaria", label: "Carga horaria (horas)", type: "number" },
];

/** Campos editables (TeachingActivityUpdate). */
export const ACTIVITY_EDIT_FIELDS: FieldConfig[] = [
  { name: "descripcion", label: "Descripción", type: "text" },
  { name: "carga_horaria", label: "Carga horaria (horas)", type: "number" },
  {
    name: "tipo_actividad",
    label: "Tipo de actividad",
    type: "select",
    optionsEndpoint: "activity-types",
  },
  {
    name: "servicio_area",
    label: "Servicio / área",
    type: "select",
    optionsEndpoint: "service-areas",
  },
];
