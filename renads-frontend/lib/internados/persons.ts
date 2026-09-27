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

const tipoDocLabel = (r: WithId): string => {
  const d = r.tipo_documento_identidad_detalle;
  if (d && typeof d === "object" && "codigo" in d) return String((d as { codigo?: unknown }).codigo ?? "—");
  if (d && typeof d === "object" && "nombre" in d) return String((d as { nombre?: unknown }).nombre ?? "—");
  return r.tipo_documento_identidad != null ? String(r.tipo_documento_identidad) : "—";
};

const universidadesLabel = (r: WithId): string => {
  const us = r.universidades;
  if (!Array.isArray(us) || us.length === 0) return "—";
  // Si el backend devuelve objetos con `siglas`, mostrarlos; si son IDs mostrar conteo.
  const first = us[0];
  if (first && typeof first === "object" && "siglas" in first) {
    return (us as { siglas?: unknown }[])
      .map((u) => String(u.siglas ?? "?"))
      .join(", ");
  }
  return `${us.length} univ.`;
};

/** Columnas base (todos los roles). */
const tutorColumnsBase: ColumnConfig<WithId>[] = [
  { key: "tipo_documento_identidad", header: "Tipo doc.", render: tipoDocLabel },
  { key: "numero_documento", header: "N° documento", render: (r) => String(r.numero_documento ?? "—") },
  { key: "apellidos_nombres", header: "Apellidos y nombres", render: (r) => apellidosNombres(r) },
  { key: "profesion", header: "Profesión", render: (r) => detalleNombre(r.profesion_detalle) },
  { key: "telefono", header: "Teléfono", render: (r) => String(r.telefono ?? "—") },
];

/** Columna «Universidades» visible solo para Administrador RENADS. */
const tutorColUniversidades: ColumnConfig<WithId> = {
  key: "universidades",
  header: "Universidades",
  render: universidadesLabel,
};

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
    { name: "apellido_materno", label: "Apellido materno", type: "text", required: true, uppercase: true },
    {
      name: "sexo",
      label: "Sexo",
      type: "select",
      required: true,
      choices: [
        { value: "M", label: "Masculino" },
        { value: "F", label: "Femenino" },
      ],
    },
    { name: "fecha_nacimiento", label: "Fecha de nacimiento", type: "date", required: true },

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
            required: true,
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
            required: true,
            optionsEndpoint: "specialties",
          } as FieldConfig,
        ]),
    // `periodo_internado` y `codigo_universitario` eliminados del form:
    // el período se inyecta desde la vista principal vía `fixedValues`; el código universitario se quitó del modelo.
    {
      name: "nota_promedio_ponderado",
      label: "Promedio ponderado promocional (##.9999)",
      type: "number",
      required: true,
      min: 0,
      max: 20,
      decimals: 4,
    },

    { name: "_s3", label: "Contacto", type: "separator" },
    { name: "correo", label: "Correo personal", type: "email", required: true },
    { name: "telefono", label: "Teléfono móvil personal", type: "text", required: true, uppercase: false, numericOnly: true },
    { name: "direccion", label: "Dirección", type: "text", required: true, uppercase: true },
    {
      name: "ubigeo",
      label: "Ubigeo",
      type: "select",
      required: true,
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
    { name: "contacto_emergencia_nombre", label: "Nombre y apellidos", type: "text", required: true, uppercase: true },
    { name: "contacto_emergencia_telefono", label: "Teléfono móvil", type: "text", required: true, uppercase: false, numericOnly: true },
    {
      name: "contacto_emergencia_parentesco",
      label: "Parentesco",
      type: "select",
      required: true,
      optionsEndpoint: "relationship-types",
    },

    { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
  ];

  // En edición: `nombres`/`direccion` como media columna para aprovechar el layout 2-col.
  const editFields: FieldConfig[] = fields.map((f) =>
    f.name === "nombres" || f.name === "direccion"
      ? { ...f, fullWidth: false }
      : f,
  );

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
    editFields,
    dialogClassName: "sm:max-w-3xl",
    editFormClassName:
      "grid max-h-[80vh] grid-cols-1 gap-x-5 gap-y-2 overflow-x-hidden overflow-y-auto px-2 py-1 sm:grid-cols-2",
    createFormClassName:
      "grid max-h-[80vh] grid-cols-1 gap-x-5 gap-y-2 overflow-x-hidden overflow-y-auto px-2 py-1 sm:grid-cols-2",
  };
}

export const TUTOR_FIELDS: FieldConfig[] = [
  { name: "_s1", label: "Identificación", type: "separator" },
  {
    name: "tipo_documento_identidad",
    label: "Tipo de documento",
    type: "select",
    required: true,
    optionsEndpoint: "identity-document-types",
  },
  { name: "numero_documento", label: "Número de documento", type: "text", required: true, docNumberFor: "tipo_documento_identidad" },

  { name: "_s2", label: "Datos personales", type: "separator" },
  { name: "nombres", label: "Nombres", type: "text", required: true, uppercase: true },
  { name: "apellido_paterno", label: "Apellido paterno", type: "text", required: true, uppercase: true },
  { name: "apellido_materno", label: "Apellido materno", type: "text", required: true, uppercase: true },

  { name: "_s3", label: "Datos profesionales", type: "separator" },
  {
    name: "profesion",
    label: "Profesión",
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
  { name: "numero_colegiatura", label: "N° colegiatura", type: "text", required: true, uppercase: false },
  {
    // RN-24 actualizada: hasta 5 universidades por tutor.
    // NOTA: el backend sigue validando máx 2 hasta que se implemente la migración correspondiente.
    name: "universidades",
    label: "Universidades (hasta 5)",
    type: "multiselect",
    required: true,
    optionsEndpoint: "universities",
  },

  { name: "_s4", label: "Contacto", type: "separator" },
  { name: "correo", label: "Correo", type: "email", required: true },
  { name: "telefono", label: "Teléfono", type: "text", required: true, uppercase: false, numericOnly: true },
  { name: "direccion", label: "Dirección", type: "text", required: true, uppercase: true },
  {
    name: "ubigeo",
    label: "Ubigeo",
    type: "select",
    required: true,
    optionsEndpoint: "ubigeos",
    optionsValueKey: "codigo",
    optionsSearchable: true,
    optionsToLabel: (r) =>
      [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")]
        .filter(Boolean)
        .join(" — "),
  },

  { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
];

/**
 * Config dinámica de tutores. Las columnas varían por rol:
 * - `Administrador RENADS`: ve la columna «Universidades» con abreviaturas de todas las asignadas.
 * - Otros roles (Universidad): solo ven los tutores de su universidad (filtro ya aplicado) sin esa columna.
 *
 * En edición:
 * - `tipo_documento_identidad` y `numero_documento` son read-only (identificador no editable).
 * - `universidades` no aparece como selector; se muestran via `renderEditInfo` desde la página.
 */
export function buildTutorsConfig(isAdmin: boolean, _universidad: number | null): ResourceConfig {
  const tutorEditFields: FieldConfig[] = TUTOR_FIELDS
    .filter((f) => f.name !== "universidades")
    .map((f) =>
      f.name === "tipo_documento_identidad" || f.name === "numero_documento"
        ? { ...f, disabled: true }
        : f,
    );

  return {
    endpoint: "tutors",
    title: "Tutores",
    singular: "tutor",
    description: "Docentes/tutores responsables.",
    searchPlaceholder: "Buscar por documento o nombres…",
    writeRoles: WRITE,
    // El alta usa el wizard de 2 pasos (TutorCreateWizard); el CRUD estándar solo edita.
    disableCreate: true,
    columns: isAdmin
      ? [...tutorColumnsBase, tutorColUniversidades]
      : tutorColumnsBase,
    filters: [{ name: "activo", label: "Activo", type: "boolean" }],
    fields: TUTOR_FIELDS,
    editFields: tutorEditFields,
    deleteConfirmDescription:
      "Se desvinculará al tutor de esta universidad. Si no tiene otras asignaciones, se eliminará su ficha completa.",
    dialogClassName: "sm:max-w-2xl",
    createFormClassName:
      "grid max-h-[80vh] grid-cols-1 gap-x-5 gap-y-2 overflow-x-hidden overflow-y-auto px-2 py-1 sm:grid-cols-2",
    editFormClassName:
      "grid max-h-[80vh] grid-cols-1 gap-x-5 gap-y-2 overflow-x-hidden overflow-y-auto px-2 py-1 sm:grid-cols-2",
  };
}

/** Columnas del listado de coordinadores. */
const coordinatorColumns: ColumnConfig<WithId>[] = [
  { key: "tipo_documento_identidad", header: "Tipo doc.", render: tipoDocLabel },
  { key: "numero_documento", header: "N° documento", render: (r) => String(r.numero_documento ?? "—") },
  { key: "apellidos_nombres", header: "Apellidos y nombres", render: (r) => apellidosNombres(r) },
  { key: "universidad", header: "Universidad", render: (r) => detalleNombre(r.universidad_detalle) },
  {
    key: "tutor",
    header: "Tutor vinculado",
    render: (r) => {
      const d = r.tutor_detalle;
      if (d && typeof d === "object" && "nombres" in d) {
        const det = d as { nombres?: unknown; apellido_paterno?: unknown };
        return [det.apellido_paterno, det.nombres].map((x) => String(x ?? "").trim()).filter(Boolean).join(" ") || "—";
      }
      return "—";
    },
  },
  { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
];

/**
 * Config CRUD de coordinadores. Sin parámetros (a diferencia de estudiantes/tutores,
 * la universidad se filtra vía `initialFilters` desde la vista, no como campo fijo).
 */
export function buildCoordinatorsConfig(): ResourceConfig {
  const fields: FieldConfig[] = [
    { name: "_s1", label: "Identificación", type: "separator" },
    {
      name: "tipo_documento_identidad",
      label: "Tipo de documento",
      type: "select",
      required: true,
      optionsEndpoint: "identity-document-types",
    },
    {
      name: "numero_documento",
      label: "Número de documento",
      type: "text",
      required: true,
      uppercase: false,
      docNumberFor: "tipo_documento_identidad",
    },

    { name: "_s2", label: "Datos personales", type: "separator" },
    { name: "nombres", label: "Nombres", type: "text", required: true, uppercase: true },
    { name: "apellido_paterno", label: "Apellido paterno", type: "text", required: true, uppercase: true },
    { name: "apellido_materno", label: "Apellido materno", type: "text", required: false, uppercase: true },

    { name: "_s4", label: "Datos profesionales", type: "separator" },
    {
      name: "universidad",
      label: "Universidad",
      type: "select",
      required: true,
      optionsEndpoint: "universities",
    },
    {
      name: "profesion",
      label: "Profesión",
      type: "select",
      required: false,
      optionsEndpoint: "professional-careers",
    },
    {
      name: "especialidad",
      label: "Especialidad",
      type: "select",
      required: false,
      optionsEndpoint: "specialties",
    },
    { name: "numero_colegiatura", label: "N° colegiatura", type: "text", required: false, uppercase: false },

    { name: "_s5", label: "Contacto", type: "separator" },
    { name: "correo", label: "Correo", type: "email", required: false },
    { name: "telefono", label: "Teléfono", type: "text", required: false, uppercase: false, numericOnly: true },
    { name: "direccion", label: "Dirección", type: "text", required: false, uppercase: true },
    {
      name: "ubigeo",
      label: "Ubigeo",
      type: "select",
      required: false,
      optionsEndpoint: "ubigeos",
      optionsValueKey: "codigo", // PK textual (mig 0048-0049)
      optionsSearchable: true,
      optionsToLabel: (r) =>
        [r.codigo, [r.distrito, r.provincia, r.departamento].filter(Boolean).join(", ")]
          .filter(Boolean)
          .join(" — "),
    },

    { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
  ];

  const editFields: FieldConfig[] = fields.map((f) =>
    f.name === "tipo_documento_identidad" || f.name === "numero_documento" || f.name === "universidad"
      ? { ...f, disabled: true }
      : f,
  );

  return {
    endpoint: "coordinators",
    title: "Coordinadores",
    singular: "coordinador",
    description: "Coordinadores de tutores por sede docente.",
    searchPlaceholder: "Buscar por documento o nombres…",
    writeRoles: WRITE,
    columns: coordinatorColumns,
    filters: [
      { name: "activo", label: "Activo", type: "boolean" },
      { name: "universidad", label: "Universidad", type: "select", optionsEndpoint: "universities" },
      {
        name: "sedes__ipress",
        label: "IPRESS",
        type: "select",
        optionsEndpoint: "ipress",
        optionsValueKey: "codigo_renipress",
        optionsSearchable: true,
      },
    ],
    fields,
    editFields,
    dialogClassName: "sm:max-w-2xl",
    createFormClassName:
      "grid max-h-[80vh] grid-cols-1 gap-x-5 gap-y-2 overflow-x-hidden overflow-y-auto px-2 py-1 sm:grid-cols-2",
    editFormClassName:
      "grid max-h-[80vh] grid-cols-1 gap-x-5 gap-y-2 overflow-x-hidden overflow-y-auto px-2 py-1 sm:grid-cols-2",
  };
}

/** Configuración de personas del módulo Internados (solo students; tutors usa `buildTutorsConfig`). */
export const PERSON_CONFIGS: Record<string, ResourceConfig> = {};

export const PERSON_MENU: { slug: string; title: string }[] = [
  { slug: "students", title: "Estudiantes" },
  { slug: "tutors", title: "Tutores" },
  { slug: "coordinators", title: "Coordinadores" },
];
