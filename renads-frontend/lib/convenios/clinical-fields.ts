import type { ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

/**
 * Configuración de los dos sub-módulos de **campos clínicos** del módulo Convenios:
 *
 * - `clinical-field-registrations` (CONAPRES): total de campos clínicos por sede docente +
 *   carrera profesional. Expone `campos_clinicos_asignados` (acumulador, solo lectura) y
 *   `disponibilidad` (registrados − asignados).
 * - `clinical-field-allocations` (Órgano Regional): cupos por universidad contra un registro.
 *   La sede/carrera/especialidad/universidad se derivan en el backend del registro padre y del
 *   convenio; el formulario solo pide el registro, el convenio, las fechas y la cantidad.
 *
 * La escritura se restringe por `writeRoles` (el backend es la autoridad final:
 * `IsConapresOrReadOnly` / `IsRegionalOrganOrReadOnly`).
 */

/** Lee un campo de un objeto `*_detalle` de FK (o «—»). */
const detalle = (v: unknown, campo: string): string =>
  v && typeof v === "object" && campo in v
    ? String((v as Record<string, unknown>)[campo] ?? "—")
    : "—";

/** Etiqueta del select de convenios (título o código). */
const convenioLabel = (r: WithId) => String(r.titulo ?? r.codigo ?? r.id);

/** Etiqueta de una IPRESS. */
const ipressLabel = (r: WithId) =>
  [r.codigo_renipress, r.nombre].filter(Boolean).join(" — ") || String(r.id);

/**
 * Etiqueta de un registro de campos clínicos (para el select del alta de asignación):
 * sede — carrera (especialidad) · disp. N. Lee los `*_detalle` que expone el backend.
 */
const registroLabel = (r: WithId) => {
  const sede = detalle(r.ipress_detalle, "nombre");
  const carrera = detalle(r.carrera_profesional_detalle, "nombre");
  const esp =
    r.especialidad_detalle && typeof r.especialidad_detalle === "object"
      ? ` (${detalle(r.especialidad_detalle, "nombre")})`
      : "";
  const disp = r.disponibilidad ?? "—";
  return `${sede} — ${carrera}${esp} · disp. ${disp}`;
};

export const clinicalFieldRegistrationsConfig: ResourceConfig = {
  endpoint: "clinical-field-registrations",
  title: "Registro de campos clínicos",
  singular: "registro de campos clínicos",
  description:
    "Total de campos clínicos por sede docente y carrera profesional (mantenimiento CONAPRES).",
  writeRoles: ["CONAPRES"],
  searchPlaceholder: "Buscar…",
  columns: [
    { key: "ipress", header: "Sede docente", render: (r) => detalle(r.ipress_detalle, "nombre") },
    {
      key: "carrera_profesional",
      header: "Carrera",
      render: (r) => detalle(r.carrera_profesional_detalle, "nombre"),
    },
    {
      key: "especialidad",
      header: "Especialidad",
      render: (r) =>
        r.especialidad_detalle ? detalle(r.especialidad_detalle, "nombre") : "—",
    },
    {
      key: "convenio",
      header: "Convenio",
      render: (r) => detalle(r.convenio_detalle, "titulo"),
    },
    { key: "campos_clinicos_registrados", header: "Registrados" },
    { key: "campos_clinicos_asignados", header: "Asignados" },
    { key: "disponibilidad", header: "Disponibles" },
  ],
  filters: [
    { name: "convenio", label: "Convenio", type: "select", optionsEndpoint: "conventions", optionsToLabel: convenioLabel },
    { name: "ipress", label: "Sede docente", type: "select", optionsEndpoint: "ipress", optionsToLabel: ipressLabel },
    {
      name: "carrera_profesional",
      label: "Carrera",
      type: "select",
      optionsEndpoint: "professional-careers",
    },
    { name: "especialidad", label: "Especialidad", type: "select", optionsEndpoint: "specialties" },
  ],
  fields: [
    {
      name: "convenio",
      label: "Convenio (Específico)",
      type: "select",
      required: true,
      optionsEndpoint: "conventions",
      optionsToLabel: convenioLabel,
      fullWidth: true,
    },
    {
      name: "ipress",
      label: "Sede docente",
      type: "select",
      required: true,
      optionsEndpoint: "ipress",
      optionsParams: { es_sede_docente: "true" },
      optionsToLabel: ipressLabel,
    },
    {
      name: "carrera_profesional",
      label: "Carrera profesional",
      type: "select",
      required: true,
      optionsEndpoint: "professional-careers",
    },
    { name: "especialidad", label: "Especialidad", type: "select", optionsEndpoint: "specialties" },
    {
      name: "campos_clinicos_registrados",
      label: "Campos clínicos registrados",
      type: "number",
      required: true,
    },
  ],
};

export const clinicalFieldAllocationsConfig: ResourceConfig = {
  endpoint: "clinical-field-allocations",
  title: "Asignación de campos clínicos",
  singular: "asignación de campos clínicos",
  description:
    "Cupos de campos clínicos por universidad, contra un registro (mantenimiento Órgano Regional).",
  writeRoles: ["Gobierno Regional"],
  searchPlaceholder: "Buscar…",
  columns: [
    { key: "ipress", header: "Sede docente", render: (r) => detalle(r.ipress_detalle, "nombre") },
    {
      key: "carrera_profesional",
      header: "Carrera",
      render: (r) => detalle(r.carrera_profesional_detalle, "nombre"),
    },
    {
      key: "universidad",
      header: "Universidad",
      render: (r) => detalle(r.universidad_detalle, "nombre"),
    },
    {
      key: "convenio",
      header: "Convenio",
      render: (r) => detalle(r.convenio_detalle, "titulo"),
    },
    { key: "campos_clinicos_autorizados", header: "Autorizados" },
    { key: "fecha_inicio", header: "Desde" },
    { key: "fecha_fin", header: "Hasta" },
  ],
  filters: [
    {
      name: "campo_clinico_ipress",
      label: "Registro",
      type: "select",
      optionsEndpoint: "clinical-field-registrations",
      optionsToLabel: registroLabel,
    },
    { name: "convenio", label: "Convenio", type: "select", optionsEndpoint: "conventions", optionsToLabel: convenioLabel },
    { name: "ipress", label: "Sede docente", type: "select", optionsEndpoint: "ipress", optionsToLabel: ipressLabel },
    {
      name: "carrera_profesional",
      label: "Carrera",
      type: "select",
      optionsEndpoint: "professional-careers",
    },
    { name: "universidad", label: "Universidad", type: "select", optionsEndpoint: "universities" },
  ],
  // Solo se envían estos campos: la sede/carrera/especialidad/universidad las deriva el backend
  // (del registro y del convenio). El registro trae su `disponibilidad` en la etiqueta.
  fields: [
    {
      name: "campo_clinico_ipress",
      label: "Registro de campos clínicos",
      type: "select",
      required: true,
      optionsEndpoint: "clinical-field-registrations",
      optionsToLabel: registroLabel,
      fullWidth: true,
    },
    {
      name: "convenio",
      label: "Convenio (Específico y vigente)",
      type: "select",
      required: true,
      optionsEndpoint: "conventions",
      optionsToLabel: convenioLabel,
      fullWidth: true,
    },
    { name: "fecha_inicio", label: "Fecha de inicio", type: "date", required: true },
    { name: "fecha_fin", label: "Fecha de fin", type: "date", required: true },
    {
      name: "campos_clinicos_autorizados",
      label: "Campos clínicos autorizados",
      type: "number",
      required: true,
    },
  ],
};
