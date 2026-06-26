import type { ResourceConfig } from "@/lib/crud/types";

const siNo = (v: unknown) => (v ? "Sí" : "No");
const WRITE = ["Universidad", "Administrador RENADS"];

const personColumns = [
  { key: "numero_documento", header: "Documento" },
  { key: "nombres", header: "Nombres" },
  { key: "apellido_paterno", header: "Apellido paterno" },
  { key: "activo", header: "Activo", render: (r: Record<string, unknown>) => siNo(r.activo) },
];

/** Configuración de personas del módulo Internados (interns, tutors). */
export const PERSON_CONFIGS: Record<string, ResourceConfig> = {
  interns: {
    endpoint: "interns",
    title: "Internos",
    singular: "interno",
    description: "Estudiantes en internado.",
    searchPlaceholder: "Buscar por documento o nombres…",
    writeRoles: WRITE,
    columns: personColumns,
    fields: [
      { name: "numero_documento", label: "Número de documento", type: "text", required: true },
      {
        name: "tipo_documento_identidad",
        label: "Tipo de documento",
        type: "select",
        required: true,
        optionsEndpoint: "identity-document-types",
      },
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
      { name: "codigo_universitario", label: "Código universitario", type: "text" },
      { name: "anio_academico", label: "Año académico", type: "number" },
      { name: "correo", label: "Correo", type: "email" },
      { name: "telefono", label: "Teléfono", type: "text" },
      { name: "direccion", label: "Dirección", type: "text" },
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
    fields: [
      { name: "numero_documento", label: "Número de documento", type: "text", required: true },
      {
        name: "tipo_documento_identidad",
        label: "Tipo de documento",
        type: "select",
        required: true,
        optionsEndpoint: "identity-document-types",
      },
      { name: "nombres", label: "Nombres", type: "text", required: true },
      { name: "apellido_paterno", label: "Apellido paterno", type: "text", required: true },
      { name: "apellido_materno", label: "Apellido materno", type: "text" },
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
  { slug: "interns", title: "Internos" },
  { slug: "tutors", title: "Tutores" },
];
