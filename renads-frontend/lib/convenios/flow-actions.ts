import type { FlowAction } from "@/lib/crud/flow-action";

/** Acciones de flujo de un convenio (ver docs/api-convenios.md). */
export const FLOW_ACTIONS: FlowAction[] = [
  {
    key: "cambiar-estado",
    label: "Cambiar estado",
    roles: ["Administrador RENADS"],
    fields: [
      {
        name: "estado_codigo",
        label: "Estado",
        type: "select",
        required: true,
        optionsEndpoint: "convention-statuses",
        optionsValueKey: "codigo",
        optionsToLabel: (row) => String(row.nombre ?? row.codigo ?? row.id),
      },
      { name: "observacion", label: "Observación", type: "text", uppercase: false },
    ],
  },
  {
    key: "evaluacion-tecnica",
    label: "Evaluación técnica",
    roles: ["DIGEP"],
    fields: [
      {
        name: "resultado",
        label: "Resultado",
        type: "select",
        required: true,
        choices: [
          { value: "VALIDADO", label: "Validado" },
          { value: "OBSERVADO", label: "Observado" },
        ],
      },
      { name: "fecha_evaluacion", label: "Fecha de evaluación", type: "date" },
      {
        name: "organo_directorio",
        label: "Órgano del directorio",
        type: "select",
        optionsEndpoint: "organ-directories",
      },
      { name: "observaciones", label: "Observaciones", type: "text", uppercase: false },
      { name: "subsanacion", label: "Subsanación", type: "text", uppercase: false },
      { name: "nomenclatura", label: "Nomenclatura (solo Marco)", type: "text", uppercase: false },
    ],
  },
  {
    key: "opinion-conapres",
    label: "Opinión CONAPRES",
    roles: ["CONAPRES"],
    onlyEspecifico: true,
    fields: [
      { name: "fecha_solicitud", label: "Fecha de solicitud", type: "date" },
      { name: "estado_atencion", label: "Estado de atención", type: "text", uppercase: false },
      { name: "resultado_opinion", label: "Resultado de la opinión", type: "text", uppercase: false },
      { name: "fecha_respuesta", label: "Fecha de respuesta", type: "date" },
    ],
  },
  {
    key: "opinion-juridica",
    label: "Opinión jurídica",
    roles: ["OGAJ"],
    fields: [
      { name: "fecha_envio", label: "Fecha de envío", type: "date" },
      { name: "resultado_opinion", label: "Resultado de la opinión", type: "text", uppercase: false },
      { name: "observaciones_legales", label: "Observaciones legales", type: "text", uppercase: false },
      { name: "subsanacion", label: "Subsanación", type: "text", uppercase: false },
      { name: "fecha_respuesta", label: "Fecha de respuesta", type: "date" },
    ],
  },
  {
    key: "firma",
    label: "Registrar firma",
    roles: ["Secretaría General"],
    fields: [
      {
        name: "firmante_tipo_contenido",
        label: "Tipo de entidad firmante (ContentType id)",
        type: "number",
        required: true,
      },
      { name: "firmante_id_objeto", label: "Id de la entidad firmante", type: "number", required: true },
      {
        name: "tipo_autoridad_firmante",
        label: "Tipo de autoridad firmante",
        type: "select",
        optionsEndpoint: "signing-authority-types",
      },
      { name: "orden_firma", label: "Orden de firma", type: "number" },
      { name: "fecha_envio", label: "Fecha de envío", type: "date" },
      { name: "fecha_recepcion", label: "Fecha de recepción", type: "date" },
      { name: "estado_firma", label: "Estado de firma", type: "text", uppercase: false },
      { name: "observaciones", label: "Observaciones", type: "text", uppercase: false },
    ],
  },
  {
    key: "publicacion",
    label: "Publicar",
    roles: ["Secretaría General"],
    fields: [
      { name: "fecha_publicacion", label: "Fecha de publicación", type: "date", required: true },
      { name: "referencia_publicacion", label: "Referencia de publicación", type: "text", uppercase: false },
    ],
  },
  {
    key: "adenda",
    label: "Crear adenda",
    roles: ["Administrador RENADS"],
    fields: [
      { name: "titulo", label: "Título (opcional)", type: "text", uppercase: false },
      { name: "fecha_inicio", label: "Fecha de inicio", type: "date", required: true },
      { name: "fecha_solicitud", label: "Fecha de solicitud", type: "date" },
      { name: "fecha_fin", label: "Fecha de fin", type: "date" },
    ],
  },
  {
    key: "participantes",
    label: "Agregar participante",
    roles: ["Administrador RENADS"],
    fields: [
      {
        name: "tipo_contenido",
        label: "Tipo de entidad (ContentType id)",
        type: "number",
        required: true,
      },
      { name: "id_objeto", label: "Id de la entidad", type: "number", required: true },
      {
        name: "tipo_autoridad_firmante",
        label: "Tipo de autoridad firmante",
        type: "select",
        optionsEndpoint: "signing-authority-types",
      },
      { name: "es_firmante", label: "¿Es firmante?", type: "boolean" },
    ],
  },
];
