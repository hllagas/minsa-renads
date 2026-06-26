import type { FlowAction } from "@/lib/crud/flow-action";
import type { WithId } from "@/lib/api/query";

const tutorLabel = (row: WithId) =>
  `${row.nombres ?? ""} ${row.apellido_paterno ?? ""} (${row.numero_documento ?? row.id})`.trim();

/** Acciones de flujo del internado (`internships/{id}/{key}/`). */
export const INTERNSHIP_ACTIONS: FlowAction[] = [
  {
    key: "cambiar-estado",
    label: "Cambiar estado",
    roles: ["Administrador RENADS"],
    fields: [
      { name: "estado_codigo", label: "Código de estado", type: "text", required: true },
      { name: "observacion", label: "Observación", type: "text" },
    ],
  },
  {
    key: "cambiar-tutor",
    label: "Cambiar tutor",
    roles: ["Universidad"],
    fields: [
      {
        name: "tutor",
        label: "Nuevo tutor",
        type: "select",
        required: true,
        optionsEndpoint: "tutors",
        optionsToLabel: tutorLabel,
      },
      { name: "fecha_cambio", label: "Fecha de cambio", type: "date", required: true },
      { name: "motivo", label: "Motivo", type: "text", required: true },
    ],
  },
  {
    key: "rotaciones",
    label: "Agregar rotación",
    roles: ["Universidad"],
    fields: [
      { name: "ipress_origen", label: "Sede de origen", type: "select", required: true, optionsEndpoint: "ipress" },
      { name: "ipress_destino", label: "Sede de destino", type: "select", required: true, optionsEndpoint: "ipress" },
      {
        name: "servicio_area",
        label: "Servicio / área",
        type: "select",
        required: true,
        optionsEndpoint: "service-areas",
      },
      { name: "fecha_inicio", label: "Fecha de inicio", type: "date" },
      { name: "fecha_fin", label: "Fecha de fin", type: "date" },
      { name: "observaciones", label: "Observaciones", type: "text" },
    ],
  },
];

/** Acciones de flujo de una rotación (`rotations/{id}/{key}/`). */
export const ROTATION_ACTIONS: FlowAction[] = [
  {
    key: "autorizar",
    label: "Autorizar",
    roles: ["Autoridad de convenio"],
    fields: [
      {
        name: "participante_convenio",
        label: "Participante del convenio (id, debe ser firmante)",
        type: "number",
        required: true,
      },
      {
        name: "resultado",
        label: "Resultado",
        type: "select",
        required: true,
        choices: [
          { value: "APROBADO", label: "Aprobado" },
          { value: "OBSERVADO", label: "Observado" },
          { value: "RECHAZADO", label: "Rechazado" },
        ],
      },
      { name: "fecha_autorizacion", label: "Fecha de autorización", type: "date" },
      { name: "observaciones", label: "Observaciones", type: "text" },
    ],
  },
  {
    key: "iniciar",
    label: "Iniciar",
    roles: ["Universidad"],
    fields: [],
  },
  {
    key: "cambiar-estado",
    label: "Cambiar estado",
    roles: ["Administrador RENADS"],
    fields: [
      { name: "estado_codigo", label: "Código de estado", type: "text", required: true },
      { name: "observacion", label: "Observación", type: "text" },
    ],
  },
];
