import type { FilterConfig, ResourceConfig } from "@/lib/crud/types";

const siNo = (v: unknown) => (v ? "Sí" : "No");
const WRITE = ["Universidad", "Administrador RENADS"];

/** Filtros declarativos de estudiantes (django-filter). `numero_documento` ya lo cubre el search. */
const studentFilters: FilterConfig[] = [
  {
    name: "universidad",
    label: "Universidad",
    type: "select",
    optionsEndpoint: "universities",
  },
  {
    name: "carrera_profesional",
    label: "Carrera profesional",
    type: "select",
    optionsEndpoint: "professional-careers",
  },
  { name: "activo", label: "Activo", type: "boolean" },
];

const personColumns = [
  { key: "numero_documento", header: "Documento" },
  { key: "nombres", header: "Nombres" },
  { key: "apellido_paterno", header: "Apellido paterno" },
  { key: "activo", header: "Activo", render: (r: Record<string, unknown>) => siNo(r.activo) },
];

/** Configuración de personas del módulo Internados (students, tutors). */
export const PERSON_CONFIGS: Record<string, ResourceConfig> = {
  students: {
    endpoint: "students",
    title: "Estudiantes",
    singular: "estudiante",
    description: "Estudiantes en proceso de internado.",
    searchPlaceholder: "Buscar por documento o nombres…",
    writeRoles: WRITE,
    columns: personColumns,
    filters: studentFilters,
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
        name: "sexo",
        label: "Sexo",
        type: "select",
        choices: [
          { value: "M", label: "Masculino" },
          { value: "F", label: "Femenino" },
        ],
      },
      { name: "fecha_nacimiento", label: "Fecha de nacimiento", type: "date" },
      {
        name: "universidad",
        label: "Universidad",
        type: "select",
        required: true,
        optionsEndpoint: "universities",
      },
      {
        name: "carrera_profesional",
        label: "Carrera profesional",
        type: "select",
        required: true,
        optionsEndpoint: "professional-careers",
      },
      {
        name: "especialidad",
        label: "Especialidad",
        type: "select",
        optionsEndpoint: "specialties",
      },
      {
        name: "periodo_academico",
        label: "Periodo académico",
        type: "select",
        optionsEndpoint: "academic-periods",
      },
      { name: "codigo_universitario", label: "Código universitario", type: "text" },
      { name: "anio_academico", label: "Año académico", type: "number" },
      {
        name: "nota_promedio_ponderado",
        label: "Nota promedio ponderado (0–20)",
        type: "number",
      },
      { name: "correo", label: "Correo personal", type: "email" },
      { name: "telefono", label: "Teléfono", type: "text" },
      { name: "direccion", label: "Dirección", type: "text" },
      {
        name: "ubigeo",
        label: "Ubigeo",
        type: "select",
        optionsEndpoint: "ubigeos",
        optionsToLabel: (r) =>
          [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")]
            .filter(Boolean)
            .join(" — "),
      },
      // El contacto de emergencia se registra en el internado, no en el estudiante
      // (migración 0015_move_emergency_contact_to_internship). Ver `INTERNSHIP_FIELDS`.
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },

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
        name: "especialidad",
        label: "Especialidad",
        type: "select",
        optionsEndpoint: "specialties",
      },
      { name: "ipress", label: "IPRESS", type: "select", optionsEndpoint: "ipress" },
      { name: "numero_colegiatura", label: "Número de colegiatura", type: "text" },
      { name: "correo", label: "Correo", type: "email" },
      { name: "telefono", label: "Teléfono", type: "text" },
      { name: "direccion", label: "Dirección", type: "text" },
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
};

export const PERSON_MENU: { slug: string; title: string }[] = [
  { slug: "students", title: "Estudiantes" },
  { slug: "tutors", title: "Tutores" },
];
