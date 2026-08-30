import type { ResourceConfig } from "@/lib/crud/types";

const siNo = (v: unknown) => (v ? "Sí" : "No");

const SEXO_CHOICES = [
  { value: "M", label: "Masculino" },
  { value: "F", label: "Femenino" },
];

const sexoLabel = (v: unknown) => {
  if (v === "M") return "Masculino";
  if (v === "F") return "Femenino";
  return "—";
};

/**
 * Config CRUD de `organ-representatives` (modelo v2, FK directa a `organo_directorio`).
 * ALTA habilitada: el backend delega en `registrar_organo_representante` (baja automática
 * del representante anterior del mismo par `organo_directorio × cargo_ejecutivo`).
 */
export const REPRESENTATIVES_CONFIG: ResourceConfig = {
  endpoint: "organ-representatives",
  title: "Representantes",
  singular: "representante",
  createPrefix: "Nuevo",
  description:
    "Representantes vigentes de órganos del directorio (MINSA, Gobierno Regional, Unidad Ejecutora, IPRESS, CONAPRES).",
  searchPlaceholder: "Buscar por nombre o N° documento…",
  columns: [
    { key: "nombre", header: "Nombre" },
    {
      key: "numero_documento_identidad",
      header: "N° documento",
    },
    {
      key: "sexo",
      header: "Sexo",
      render: (r) => sexoLabel(r.sexo),
    },
    {
      key: "fecha_inicio_designacion",
      header: "Inicio designación",
    },
    { key: "activo", header: "Activo", render: (r) => siNo(r.activo) },
  ],
  filters: [
    {
      name: "organo_directorio",
      label: "Órgano del directorio",
      type: "select",
      optionsEndpoint: "organ-directories",
    },
    {
      name: "cargo_ejecutivo",
      label: "Cargo ejecutivo",
      type: "select",
      optionsEndpoint: "executive-positions",
    },
    { name: "activo", label: "Activo", type: "boolean" },
  ],
  fields: [
    { name: "_s1", label: "Datos personales", type: "separator" },
    { name: "nombre", label: "Nombre completo", type: "text", required: true, fullWidth: true, uppercase: false },
    {
      name: "tipo_documento_identidad",
      label: "Tipo de documento",
      type: "select",
      required: true,
      optionsEndpoint: "identity-document-types",
    },
    { name: "numero_documento_identidad", label: "N° documento", type: "text", required: true, uppercase: false },
    {
      name: "sexo",
      label: "Sexo",
      type: "select",
      required: true,
      choices: SEXO_CHOICES,
    },

    { name: "_s2", label: "Designación", type: "separator" },
    {
      name: "organo_directorio",
      label: "Órgano del directorio",
      type: "select",
      required: true,
      optionsEndpoint: "organ-directories",
    },
    {
      name: "cargo_ejecutivo",
      label: "Cargo ejecutivo",
      type: "select",
      required: true,
      optionsEndpoint: "executive-positions",
    },
    { name: "fecha_inicio_designacion", label: "Fecha de designación", type: "date", required: true },
    { name: "numero_resolucion_designacion", label: "N° resolución de designación", type: "text", uppercase: false },
    { name: "fecha_inicio_facultades", label: "Fecha de inicio de facultades", type: "date" },

    { name: "_s3", label: "Estado", type: "separator" },
    { name: "activo", label: "Activo", type: "boolean", defaultValue: true },
  ],
};
