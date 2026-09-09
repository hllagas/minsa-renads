import type { ColumnConfig, FieldConfig, ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

const siNo = (v: unknown) => (v ? "Sí" : "No");
const WRITE = ["Universidad", "Administrador RENADS"];

const detalleNombre = (v: unknown): string =>
  v && typeof v === "object" && "nombre" in v
    ? String((v as { nombre?: unknown }).nombre ?? "—")
    : "—";

/** «Apellidos y nombres» en un solo campo (el backend no expone `nombre_completo`). */
const apellidosNombres = (r: WithId): string =>
  [r.apellido_paterno, r.apellido_materno, r.nombres]
    .map((x) => String(x ?? "").trim())
    .filter(Boolean)
    .join(" ");

const personColumns = [
  { key: "numero_documento", header: "Documento" },
  { key: "nombres", header: "Nombres" },
  { key: "apellido_paterno", header: "Apellido paterno" },
  { key: "activo", header: "Activo", render: (r: Record<string, unknown>) => siNo(r.activo) },
];

/** Columnas del listado de estudiantes (requerimiento: carrera, documento, apellidos+nombres, nota). */
const studentColumns: ColumnConfig<WithId>[] = [
  { key: "carrera_profesional", header: "Carrera profesional", render: (r) => detalleNombre(r.carrera_profesional_detalle) },
  { key: "numero_documento", header: "N° documento" },
  { key: "apellidos_nombres", header: "Apellidos y nombres", render: (r) => apellidosNombres(r) },
  { key: "nota_promedio_ponderado", header: "Nota promedio", render: (r) => String(r.nota_promedio_ponderado ?? "—") },
  { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
];

/**
 * Config CRUD de estudiantes. `pregradoId` (id del nivel «Pregrado», resuelto en runtime desde
 * `academic-levels`) dirige el toggle del form: nivel «Pregrado» → carrera profesional; otro nivel
 * → especialidad (RN-19). El nivel es un campo **virtual** (`_nivel`, solo UI, no se envía; el
 * backend deriva el nivel de la carrera/especialidad). La universidad se fija por la vista principal
 * (`fixedValues` → oculta el campo). `undefined`/`null` en `pregradoId` degrada a mostrar ambos
 * selects (el catálogo aún no cargó).
 */
export function buildStudentsConfig(pregradoId: number | null): ResourceConfig {
  const esPregrado = (v: Record<string, unknown>) =>
    pregradoId != null && v._nivel === pregradoId;
  const esOtroNivel = (v: Record<string, unknown>) =>
    v._nivel != null && v._nivel !== "" && v._nivel !== pregradoId;

  const fields: FieldConfig[] = [
    { name: "_s1", label: "Datos personales", type: "separator" },
    {
      name: "tipo_documento_identidad",
      label: "Tipo de documento",
      type: "select",
      required: true,
      optionsEndpoint: "identity-document-types",
    },
    { name: "numero_documento", label: "Número de documento", type: "text", required: true, uppercase: false },
    { name: "nombres", label: "Nombres", type: "text", required: true, uppercase: false },
    { name: "apellido_paterno", label: "Apellido paterno", type: "text", required: true, uppercase: false },
    { name: "apellido_materno", label: "Apellido materno", type: "text", uppercase: false },
    {
      name: "sexo",
      label: "Sexo",
      type: "select",
      choices: [
        { value: "M", label: "Masculino" },
        { value: "F", label: "Femenino" },
      ],
    },
    { name: "fecha_nacimiento", label: "Fecha de nacimiento", type: "date" },

    { name: "_s2", label: "Datos académicos", type: "separator" },
    // `universidad` la fija la vista principal (fixedValues); queda oculta del form.
    {
      name: "universidad",
      label: "Universidad",
      type: "select",
      required: true,
      optionsEndpoint: "universities",
    },
    // Nivel académico: campo VIRTUAL (no se envía) — solo alterna carrera/especialidad (RN-19).
    {
      name: "_nivel",
      label: "Nivel académico",
      type: "select",
      required: true,
      virtual: true,
      optionsEndpoint: "academic-levels",
    },
    // Pregrado → carrera profesional (filtrada por nivel Pregrado). Otro nivel → oculto.
    {
      name: "carrera_profesional",
      label: "Carrera profesional",
      type: "select",
      optionsEndpoint: "professional-careers",
      optionsParams: pregradoId != null ? { nivel_academico: String(pregradoId) } : undefined,
      showWhen: esPregrado,
      resetsOn: ["_nivel"],
    },
    // Postgrado/Doctorado → especialidad. Pregrado → oculto.
    {
      name: "especialidad",
      label: "Especialidad",
      type: "select",
      optionsEndpoint: "specialties",
      showWhen: esOtroNivel,
      resetsOn: ["_nivel"],
    },
    {
      name: "periodo_academico",
      label: "Periodo académico",
      type: "select",
      optionsEndpoint: "academic-periods",
    },
    { name: "codigo_universitario", label: "Código universitario", type: "text", uppercase: false },
    {
      name: "nota_promedio_ponderado",
      label: "Nota promedio ponderado (0–20)",
      type: "number",
    },

    { name: "_s3", label: "Contacto", type: "separator" },
    { name: "correo", label: "Correo personal", type: "email" },
    { name: "telefono", label: "Teléfono", type: "text", uppercase: false },
    { name: "direccion", label: "Dirección", type: "text", uppercase: false },
    {
      name: "ubigeo",
      label: "Ubigeo",
      type: "select",
      optionsEndpoint: "ubigeos",
      optionsValueKey: "codigo", // PK textual (mig 0048-0049)
      optionsSearchable: true,
      optionsToLabel: (r) =>
        [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")]
          .filter(Boolean)
          .join(" — "),
    },

    // Contacto de emergencia — vive en el estudiante desde la mig 0025 (2026-09-09; antes en el internado).
    { name: "_s4", label: "Contacto de emergencia", type: "separator" },
    { name: "contacto_emergencia_nombre", label: "Nombre", type: "text", uppercase: false },
    { name: "contacto_emergencia_telefono", label: "Teléfono", type: "text", uppercase: false },
    {
      name: "contacto_emergencia_parentesco",
      label: "Parentesco",
      type: "select",
      optionsEndpoint: "relationship-types",
    },

    { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
  ];

  return {
    endpoint: "students",
    title: "Estudiantes",
    singular: "estudiante",
    description: "Estudiantes en proceso de internado.",
    searchPlaceholder: "Buscar por documento o nombres…",
    writeRoles: WRITE,
    columns: studentColumns,
    filters: [
      // Filtro por nivel (default «Pregrado» lo inyecta la página vía initialFilters).
      { name: "nivel_academico", label: "Nivel académico", type: "select", optionsEndpoint: "academic-levels" },
      { name: "carrera_profesional", label: "Carrera profesional", type: "select", optionsEndpoint: "professional-careers" },
      { name: "activo", label: "Activo", type: "boolean" },
    ],
    fields,
  };
}

/** Configuración de personas del módulo Internados (solo tutors; students usa `buildStudentsConfig`). */
export const PERSON_CONFIGS: Record<string, ResourceConfig> = {
  tutors: {
    endpoint: "tutors",
    title: "Tutores",
    singular: "tutor",
    description: "Docentes/tutores responsables.",
    searchPlaceholder: "Buscar por documento o nombres…",
    writeRoles: WRITE,
    columns: personColumns,
    filters: [
      {
        name: "universidades",
        label: "Universidad",
        type: "select",
        optionsEndpoint: "universities",
      },
      { name: "activo", label: "Activo", type: "boolean" },
    ],
    fields: [
      {
        name: "tipo_documento_identidad",
        label: "Tipo de documento",
        type: "select",
        required: true,
        optionsEndpoint: "identity-document-types",
      },
      { name: "numero_documento", label: "Número de documento", type: "text", required: true },
      { name: "nombres", label: "Nombres", type: "text", required: true },
      { name: "apellido_paterno", label: "Apellido paterno", type: "text", required: true },
      { name: "apellido_materno", label: "Apellido materno", type: "text" },
      {
        // RN-24: el backend exige de 1 a 2 universidades por tutor (valida 400 si 0 o >2).
        name: "universidades",
        label: "Universidades (1 a 2)",
        type: "multiselect",
        required: true,
        optionsEndpoint: "universities",
      },
      {
        // Profesión del tutor (carrera profesional) — mig 0025 (2026-09-09).
        name: "profesion",
        label: "Profesión",
        type: "select",
        optionsEndpoint: "professional-careers",
      },
      {
        name: "especialidad",
        label: "Especialidad",
        type: "select",
        optionsEndpoint: "specialties",
      },
      { name: "ipress", label: "IPRESS", type: "select", optionsEndpoint: "ipress", optionsValueKey: "codigo_renipress", optionsSearchable: true },
      { name: "numero_colegiatura", label: "Número de colegiatura", type: "text", uppercase: false },
      { name: "correo", label: "Correo", type: "email" },
      { name: "telefono", label: "Teléfono", type: "text", uppercase: false },
      { name: "direccion", label: "Dirección", type: "text", uppercase: false },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
};

export const PERSON_MENU: { slug: string; title: string }[] = [
  { slug: "students", title: "Estudiantes" },
  { slug: "tutors", title: "Tutores" },
];
