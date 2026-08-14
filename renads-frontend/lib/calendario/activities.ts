import type { ResourceConfig } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";

/**
 * CRUD del Calendario administrativo (`calendar-activities`). Registra actividades del proyecto
 * RENADS con ventana de fechas; si `controla_acceso` está activo, los `content_types` asociados
 * quedan gobernados por el enforcement temporal del backend (una ventana vigente habilita la
 * escritura del módulo). Escritura solo `Administrador RENADS` (backend `IsAdminRoleOrReadOnly`).
 */

const siNo = (v: unknown) => (v ? "Sí" : "No");

/** Etiqueta de un ContentType (módulo/modelo): «verbose (app.model)». */
const contentTypeLabel = (r: WithId) => {
  const vn = r.verbose_name ?? r.model;
  return r.app_label ? `${vn} (${r.app_label}.${r.model})` : String(vn ?? r.id);
};

/** Etiqueta de un rol/grupo. */
const groupLabel = (r: WithId) => String(r.name ?? r.id);

export const calendarActivitiesConfig: ResourceConfig = {
  endpoint: "calendar-activities",
  title: "Calendario de actividades",
  singular: "actividad",
  description:
    "Actividades administrativas del proyecto RENADS. Las marcadas «controla acceso» habilitan la escritura de los módulos asociados durante su ventana de fechas.",
  writeRoles: ["Administrador RENADS"],
  defaultOrdering: "numero_orden",
  searchPlaceholder: "Buscar por nombre…",
  columns: [
    { key: "numero_orden", header: "N.º" },
    { key: "nombre", header: "Actividad" },
    { key: "fecha_inicio", header: "Desde" },
    { key: "fecha_fin", header: "Hasta", render: (r) => String(r.fecha_fin ?? "—") },
    { key: "controla_acceso", header: "Controla acceso", render: (r) => siNo(r.controla_acceso) },
    {
      key: "content_types_detalle",
      header: "Módulos",
      render: (r) => String((r.content_types_detalle as unknown[] | undefined)?.length ?? 0),
    },
    {
      key: "responsables_detalle",
      header: "Responsables",
      render: (r) => String((r.responsables_detalle as unknown[] | undefined)?.length ?? 0),
    },
    { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
  ],
  filters: [
    { name: "controla_acceso", label: "Controla acceso", type: "boolean" },
    { name: "activo", label: "Activo", type: "boolean" },
    {
      name: "content_types",
      label: "Módulo",
      type: "select",
      optionsEndpoint: "content-types",
      optionsToLabel: contentTypeLabel,
    },
  ],
  fields: [
    { name: "numero_orden", label: "Número de orden", type: "number", required: true },
    { name: "nombre", label: "Nombre de la actividad", type: "text", required: true, fullWidth: true },
    { name: "detalle", label: "Detalle", type: "text", fullWidth: true },
    { name: "fecha_inicio", label: "Fecha de inicio", type: "date", required: true },
    { name: "fecha_fin", label: "Fecha de fin (vacío = sin cierre)", type: "date" },
    {
      name: "responsables",
      label: "Responsables (roles)",
      type: "multiselect",
      optionsEndpoint: "groups",
      optionsToLabel: groupLabel,
    },
    {
      name: "controla_acceso",
      label: "¿Controla el acceso a módulos?",
      type: "boolean",
      defaultValue: false,
    },
    {
      name: "content_types",
      label: "Módulos/modelos asociados",
      type: "multiselect",
      optionsEndpoint: "content-types",
      optionsToLabel: contentTypeLabel,
    },
    { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
  ],
};
