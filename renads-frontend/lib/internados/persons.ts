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

/** Columnas del listado de tutores (requerimiento: colegiatura, apellidos+nombres, profesión). */
const tutorColumns: ColumnConfig<WithId>[] = [
  { key: "numero_colegiatura", header: "N° colegiatura", render: (r) => String(r.numero_colegiatura ?? "—") },
  { key: "apellidos_nombres", header: "Apellidos y nombres", render: (r) => apellidosNombres(r) },
  { key: "profesion", header: "Profesión", render: (r) => detalleNombre(r.profesion_detalle) },
  { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
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
 * Config CRUD de estudiantes. El **nivel académico se fija desde la vista general** (selector
 * superior) y llega como `nivelActivoId`: si es «Pregrado» (`pregradoId`) el form pide **carrera
 * profesional**; en otro nivel pide **especialidad** (RN-19). El nivel ya NO se pregunta en el form
 * (antes campo virtual `_nivel`, retirado — hereda el elegido en la vista). La universidad se fija
 * por la vista principal (`fixedValues` → oculta el campo). `null` en `nivelActivoId` degrada a
 * mostrar carrera (el catálogo aún no cargó).
 */
export function buildStudentsConfig(
  nivelActivoId: number | null,
  pregradoId: number | null,
): ResourceConfig {
  // Nivel fijado por la vista: Pregrado → carrera; otro → especialidad. Sin nivel resuelto → carrera.
  const esPregrado = nivelActivoId != null && nivelActivoId === pregradoId;
  const mostrarCarrera = nivelActivoId == null || esPregrado;

  const fields: FieldConfig[] = [
    { name: "_s1", label: "Datos personales", type: "separator" },
    {
      name: "tipo_documento_identidad",
      label: "Tipo de documento",
      type: "select",
      required: true,
      optionsEndpoint: "identity-document-types",
    },
    { name: "numero_documento", label: "Número de documento", type: "text", required: true, uppercase: false, docNumberFor: "tipo_documento_identidad" },
    { name: "nombres", label: "Nombres", type: "text", required: true, uppercase: true },
    { name: "apellido_paterno", label: "Apellido paterno", type: "text", required: true, uppercase: true },
    { name: "apellido_materno", label: "Apellido materno", type: "text", uppercase: true },
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
    // Nivel académico: NO se pide aquí — lo fija el selector de la vista general y determina, abajo,
    // si se muestra carrera (Pregrado) o especialidad (otro nivel).
    // Pregrado → carrera profesional (filtrada por nivel Pregrado). Otro nivel → especialidad.
    ...(mostrarCarrera
      ? [
          {
            name: "carrera_profesional",
            label: "Carrera profesional",
            type: "select",
            optionsEndpoint: "professional-careers",
            optionsParams:
              pregradoId != null ? { nivel_academico: String(pregradoId) } : undefined,
          } as FieldConfig,
        ]
      : [
          {
            name: "especialidad",
            label: "Especialidad",
            type: "select",
            optionsEndpoint: "specialties",
          } as FieldConfig,
        ]),
    {
      name: "periodo_internado",
      label: "Periodo de internado",
      type: "select",
      optionsEndpoint: "internship-periods",
    },
    { name: "codigo_universitario", label: "Código universitario", type: "text", uppercase: false },
    {
      name: "nota_promedio_ponderado",
      label: "Nota promedio ponderado (0–20)",
      type: "number",
      min: 0,
      max: 20,
      decimals: 3,
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
      // El nivel y el periodo se eligen en los selectores de la vista general (no en la barra de filtros).
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
    columns: tutorColumns,
    // La universidad se elige en el paso previo de la vista (gate por alcance) → filtro `universidades`
    // inyectado como initialFilters; aquí solo queda `activo`.
    filters: [{ name: "activo", label: "Activo", type: "boolean" }],
    fields: [
      {
        name: "tipo_documento_identidad",
        label: "Tipo de documento",
        type: "select",
        required: true,
        optionsEndpoint: "identity-document-types",
      },
      { name: "numero_documento", label: "Número de documento", type: "text", required: true, docNumberFor: "tipo_documento_identidad" },
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
      { name: "numero_colegiatura", label: "Número de colegiatura", type: "text", uppercase: false },
      { name: "correo", label: "Correo", type: "email" },
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
      { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
    ],
  },
};

export const PERSON_MENU: { slug: string; title: string }[] = [
  { slug: "students", title: "Estudiantes" },
  { slug: "tutors", title: "Tutores" },
];
