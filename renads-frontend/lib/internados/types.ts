/**
 * Tipos del módulo de Internados.
 * Contrato: docs/api-internados.md
 */

/** Lectura de un vínculo tutor × convenio × IPRESS (endpoint `/tutors/{id}/convenios/`). */
export interface TutorConvenioRead {
  /** Identificador del vínculo (equivale al `convenio_pk` en las rutas de sub-recurso). */
  id: number;
  tutor: number;
  convenio: number;
  convenio_detalle: {
    id: number;
    titulo: string;
    nomenclatura: string | null;
  };
  /** Código RENIPRESS (PK textual de la IPRESS). */
  ipress: string;
  ipress_detalle: {
    codigo_renipress: string;
    nombre: string;
  };
}

/** Lectura de un coordinador (endpoint GET /coordinators/ y /coordinators/{id}/). */
export interface CoordinatorRead {
  id: number;
  tutor: number | null;
  tutor_detalle: { id: number; nombres: string; apellido_paterno: string } | null;
  universidad: number;
  universidad_detalle: { id: number; nombre: string };
  tipo_documento_identidad: number;
  numero_documento: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  correo: string | null;
  telefono: string | null;
  numero_colegiatura: string | null;
  direccion: string | null;
  ubigeo: string | null;       // PK textual (codigo — mig 0048-0049)
  especialidad: number | null;
  profesion: number | null;
  activo: boolean;
}

/** Lectura de una sede asignada a un coordinador (endpoint /coordinators/{id}/sedes/). */
export interface CoordinatorSedeRead {
  id: number;
  coordinador: number;
  ipress: string;              // PK textual (codigo_renipress)
  universidad_detalle: { id: number; nombre: string };
  ipress_detalle: { codigo_renipress: string; nombre: string };
}

/** Lectura de un tutor asignado a una sede de coordinador (/coordinators/{id}/sedes/{sede_pk}/tutors/). */
export interface CoordinatorTutorRead {
  id: number;
  coordinador_sede: number;
  tutor: number;
  tutor_detalle: {
    id: number;
    nombres: string;
    apellido_paterno: string;
    numero_documento: string;
  };
}
