import type { FlowAction } from "@/lib/crud/flow-action";

/** Acciones de flujo de una actividad (`teaching-activities/{id}/{key}/`). */
export const ACTIVITY_ACTIONS: FlowAction[] = [
  {
    key: "validar",
    label: "Validar",
    roles: ["Tutor"],
    fields: [
      {
        name: "resultado",
        label: "Resultado",
        type: "select",
        required: true,
        choices: [
          { value: "VALIDADA", label: "Validada" },
          { value: "OBSERVADA", label: "Observada" },
          { value: "RECHAZADA", label: "Rechazada" },
        ],
      },
      { name: "comentario", label: "Comentario", type: "text" },
    ],
  },
  {
    key: "subsanar",
    label: "Subsanar",
    roles: ["Universidad", "Tutor", "Sede docente"],
    fields: [
      { name: "descripcion", label: "Descripción", type: "text" },
      { name: "carga_horaria", label: "Carga horaria (horas)", type: "number" },
    ],
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
