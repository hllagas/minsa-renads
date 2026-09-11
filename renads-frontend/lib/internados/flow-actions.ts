import type { FlowAction } from "@/lib/crud/flow-action";

/** Acciones de flujo del internado (`interns/{id}/{key}/`). */
export const INTERNSHIP_ACTIONS: FlowAction[] = [
  {
    key: "rotaciones",
    label: "Agregar rotación",
    roles: ["Universidad"],
    fields: [
      { name: "ipress_origen", label: "Sede de origen", type: "select", required: true, optionsEndpoint: "ipress", optionsValueKey: "codigo_renipress", optionsSearchable: true },
      { name: "ipress_destino", label: "Sede de destino", type: "select", required: true, optionsEndpoint: "ipress", optionsValueKey: "codigo_renipress", optionsSearchable: true },
      {
        name: "servicio_area",
        label: "Servicio / área",
        type: "select",
        required: true,
        optionsEndpoint: "service-areas",
      },
      { name: "fecha_inicio", label: "Fecha de inicio", type: "date" },
      { name: "fecha_fin", label: "Fecha de fin", type: "date" },
      { name: "observaciones", label: "Observaciones", type: "text", uppercase: false },
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
      { name: "observaciones", label: "Observaciones", type: "text", uppercase: false },
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
