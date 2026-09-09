import type { FieldConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

const personaLabel = (row: WithId) =>
  `${row.nombres ?? ""} ${row.apellido_paterno ?? ""} (${row.numero_documento ?? row.id})`.trim();
const convenioLabel = (row: WithId) => String(row.titulo ?? row.codigo ?? row.id);

// Nota: el contacto de emergencia se movió del internado al ESTUDIANTE (mig 0025, 2026-09-09).
// Ver `lib/internados/persons.ts` (buildStudentsConfig). Ya no se captura aquí.

/**
 * Campos de alta de internado (InternshipWrite). `estado_actual` y `creado_por` los fija el backend.
 * `campo_clinico` se captura como número (id) — sin selector dependiente del convenio por ahora.
 */
export const INTERNSHIP_FIELDS: FieldConfig[] = [
  {
    name: "estudiante",
    label: "Estudiante",
    type: "select",
    required: true,
    optionsEndpoint: "students",
    optionsToLabel: personaLabel,
  },
  {
    name: "convenio",
    label: "Convenio Específico",
    type: "select",
    required: true,
    optionsEndpoint: "conventions",
    optionsToLabel: convenioLabel,
  },
  { name: "campo_clinico", label: "Campo clínico (id)", type: "number", required: true },
  {
    name: "ipress",
    label: "Sede docente (IPRESS)",
    type: "select",
    required: true,
    optionsEndpoint: "ipress",
    optionsValueKey: "codigo_renipress",
    optionsSearchable: true,
    // Filtra las IPRESS por la **unidad ejecutora del convenio** elegido (p. ej. DIRIS Lima Este),
    // y solo sedes docentes autorizadas. Se resuelve el detalle del convenio para obtener su UE.
    optionsParamsFromEntity: {
      field: "convenio",
      endpoint: "conventions",
      toParams: (c: WithId) =>
        c.unidad_ejecutora
          ? { unidad_ejecutora: String(c.unidad_ejecutora), es_sede_docente: "true" }
          : undefined,
    },
    resetsOn: ["convenio"],
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
    name: "ambito_geografico_sanitario",
    label: "Ámbito geográfico sanitario",
    type: "select",
    required: true,
    optionsEndpoint: "health-geographic-scopes",
  },
  { name: "fecha_inicio", label: "Fecha de inicio", type: "date", required: true },
  { name: "fecha_fin", label: "Fecha de fin (máx. 1 año)", type: "date", required: true },
  { name: "observaciones", label: "Observaciones", type: "text", uppercase: false },
];

/** Campos editables (InternshipUpdate). El tutor se cambia con la acción `cambiar-tutor`. */
export const INTERNSHIP_EDIT_FIELDS: FieldConfig[] = [
  { name: "ipress", label: "Sede docente (IPRESS)", type: "select", optionsEndpoint: "ipress", optionsValueKey: "codigo_renipress", optionsSearchable: true },
  { name: "fecha_inicio", label: "Fecha de inicio", type: "date" },
  { name: "fecha_fin", label: "Fecha de fin", type: "date" },
  { name: "observaciones", label: "Observaciones", type: "text", uppercase: false },
];
