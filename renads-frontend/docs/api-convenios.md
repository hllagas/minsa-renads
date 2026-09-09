# API — Módulo 1: Gestionar Convenios (`apps/convenios`)

Ciclo de vida de Convenios Marco y Específicos: registro, evaluación técnica (DIGEP), opinión
CONAPRES, campos clínicos, opinión jurídica (OGAJ), firma, publicación, vigencia y cierre.
Base: `/api/v1/`. Todos los endpoints requieren JWT.

**Última revisión de contrato: 2026-09-09** (RN-1 ampliada: Marco por GORE/MINSA/Universidad;
`gobierno_regional` obligatorio solo en Marco+GORE, nulo en el resto; `organ-directories` por FK `organo`).

## Reglas de negocio clave (para validación/UX)

- Un Convenio **Marco** lo puede solicitar un órgano de categoría **Gobierno Regional
  (GERESA/DIRESA), MINSA o Universidad** (`organo_directorio` cuya `organo.categoria` ∈
  {`GOBIERNO_REGIONAL`, `ORGANO_MINSA`, `UNIVERSIDAD`} — RN-1, ampliada); no lleva `convenio_marco`,
  `unidad_ejecutora` ni `facultad`.
- **RN-3:** un Convenio **Específico** requiere un **Convenio Marco vigente**
  (estado en `VIGENTE` / `PUBLICADO` / `SUSCRITO`) — **salvo si el órgano es DIRIS**, que puede
  crear Específico sin Marco (si lo envía, igual debe estar vigente).
- CONAPRES y campos clínicos **solo aplican a convenios Específicos**.
- Un **campo clínico** solo acepta una IPRESS con **`es_sede_docente = true`** (autorizada por
  CONAPRES vía `POST /ipress/{id}/autorizar-sede-docente/` — ver `docs/api-catalogos.md`);
  si no, el backend responde error en el campo `ipress`.
- No se puede **firmar** con observaciones pendientes (evaluación técnica / CONAPRES / OGAJ `OBSERVADO` sin subsanar).
- `fecha_fin` la calcula el backend (vigencia del tipo: 4 años Marco / 3 años Específico). No enviarla.
- Un Convenio Específico requiere `unidad_ejecutora` y `facultad` (la facultad debe pertenecer a la
  universidad del Marco).
- La **adenda** hereda tipo, marco, universidad, órgano, unidad ejecutora y facultad del origen;
  solo requiere `fecha_inicio` nuevo. Al suscribirse, el convenio origen pasa a `AMPLIADO`.
- `nomenclatura` la asigna DIGEP en `evaluacion-tecnica` (campo `nomenclatura` write-only en esa
  acción); **no se envía** en el alta ni en la edición del convenio.

## Recurso núcleo — `conventions`

| Método | Ruta | Rol requerido | Notas |
|--------|------|---------------|-------|
| GET | `/conventions/` | autenticado (alcance) | lista; filtros abajo |
| GET | `/conventions/{id}/` | autenticado (alcance) | detalle |
| POST | `/conventions/` | dentro de su ámbito | crear (estado inicial `SOLICITUD_REGISTRADA`) |
| PUT/PATCH | `/conventions/{id}/` | dentro de su ámbito | actualizar |
| POST | `/conventions/{id}/cambiar-estado/` | `Administrador RENADS` | `{ estado_codigo, observacion? }` |
| POST | `/conventions/{id}/evaluacion-tecnica/` | `DIGEP` | ver campos abajo |
| POST | `/conventions/{id}/opinion-conapres/` | `CONAPRES` | solo Específico |
| POST | `/conventions/{id}/opinion-juridica/` | `OGAJ` | |
| POST | `/conventions/{id}/firma/` | `Secretaría General` | bloquea si hay observaciones pendientes |
| POST | `/conventions/{id}/publicacion/` | `Secretaría General` | `PUBLICADO` → `VIGENTE` |
| GET·POST | `/conventions/{id}/parties/` | GET: autenticado; POST: `Administrador RENADS` | partes firmantes tipadas (sincroniza lista completa) |
| GET·POST | `/conventions/{id}/participantes/` | POST: `Administrador RENADS` | GET lista, POST agrega (legado) |
| GET | `/conventions/{id}/historial/` | autenticado | historial de estados |
| POST | `/conventions/{id}/adenda/` | dentro de su ámbito | crea adenda del convenio |

**Filtros** (`ConventionFilter`): `tipo_convenio`, `estado_actual`, `convenio_marco`,
`convenio_origen`, `es_adenda`, rangos de `fecha_solicitud` / `fecha_inicio` / `fecha_fin`, solicitante (tipo + id).
**Search:** `titulo`, `nomenclatura`. **Ordering:** `fecha_solicitud`, `fecha_inicio`, `fecha_fin`, `id`.

### Convention — lectura (`GET`)
```
id, tipo_convenio, convenio_marco, convenio_origen, es_adenda,
plantilla, nomenclatura, titulo,
solicitante_tipo_contenido, solicitante_id_objeto, solicitante,
organo_directorio, organo_directorio_nombre, tipo_organo_directorio,
gobierno_regional, gobierno_regional_detalle,
universidad, universidad_nombre, tipo_entidad_universidad,
unidad_ejecutora, unidad_ejecutora_detalle, facultad, facultad_detalle,
estado_actual, estado_codigo, fecha_solicitud, fecha_inicio, fecha_fin,
vigencia_efectiva, adendas, partes_firmantes,
max_campos_clinicos, creado_por, creado_en, actualizado_en
```

`unidad_ejecutora_detalle` → `{id, nombre, codigo}`.
`facultad_detalle` → `{id, nombre}`.
`gobierno_regional_detalle` → `{id, nombre, sigla}` (o `null`). **Refactor 2026-09-07 (mig 0041):**
el GORE se trasladó de `organo_directorio` → `convenio`; solo aplica a Convenio Marco regional
(la adenda lo hereda del origen).
`adendas` → lista `[{id, titulo, estado_codigo, fecha_inicio, fecha_fin}]`.
`vigencia_efectiva` → `{fecha_inicio, fecha_fin}` (de la última adenda activa, o del convenio).
`partes_firmantes` → lista de `ConventionParty` (ver §parties).

### Convention — escritura (`POST`/`PUT`)
```
tipo_convenio, convenio_marco, plantilla, titulo,
solicitante_tipo_contenido, solicitante_id_objeto,
organo_directorio, gobierno_regional?, universidad, unidad_ejecutora?, facultad?,
fecha_solicitud, fecha_inicio?, fecha_fin?, max_campos_clinicos?
```
> `unidad_ejecutora` y `facultad` solo aplican a Específico. `facultad` debe pertenecer a la
> universidad del Marco. `nomenclatura` no se envía (la asigna DIGEP). `gobierno_regional` solo
> aplica a **Convenio Marco + órgano de categoría Gobierno Regional** (donde es **obligatorio**);
> cualquier otra combinación (Marco MINSA/Universidad, Marco DIRIS o Específico) lo debe dejar
> **nulo** (el backend rechaza el valor). El alta filtra el órgano del directorio por una
> **categoría de órgano** (`organs`) y muestra `gobierno_regional` solo en ese caso.

### Payloads de acciones de flujo

- **evaluacion-tecnica:** `resultado, observaciones, subsanacion, organo_directorio, fecha_evaluacion, nomenclatura?`
  (`nomenclatura` write-only: solo se persiste en Marcos al `resultado=VALIDADO`).
- **opinion-conapres:** `fecha_solicitud, estado_atencion, resultado_opinion, fecha_respuesta`.
- **opinion-juridica:** `fecha_envio, resultado_opinion, observaciones_legales, subsanacion, fecha_respuesta`.
- **firma:** `firmante_tipo_contenido, firmante_id_objeto, tipo_autoridad_firmante, orden_firma, fecha_envio, fecha_recepcion, estado_firma, observaciones`.
- **publicacion:** `fecha_publicacion, referencia_publicacion`.
- **adenda:** `titulo?, nomenclatura?, fecha_solicitud?, fecha_inicio (req), fecha_fin?`.
  Hereda tipo/marco/universidad/órgano/UE/facultad del origen. Devuelve `ConventionRead`.
- **parties (POST):** array de objetos `ConventionParty` — sincroniza la lista completa.
- **participantes (POST):** `tipo_contenido, id_objeto, tipo_autoridad_firmante, es_firmante`.
- **cambiar-estado:** `{ estado_codigo, observacion? }`.

### Partes firmantes — `conventions/{id}/parties`

`ConventionParty` — campos:
```
id (ro), convenio (ro), rol, rol_display (ro),
organo_directorio, organo_directorio_detalle (ro),
organo_representante?, organo_representante_detalle (ro),
cargo_ejecutivo?, cargo_ejecutivo_detalle (ro),
orden, es_firmante, creado_en (ro)
```

`rol` choices: `MINSA` | `UNIVERSIDAD` | `GOBIERNO_REGIONAL` | `UNIDAD_EJECUTORA` | `FACULTAD`.
`organo_directorio_detalle` → `{id, nombre, siglas}`.
`organo_representante_detalle` → `{id, nombre, numero_documento_identidad}`.
`cargo_ejecutivo_detalle` → `{id, nombre_masculino, nombre_femenino}`.

POST sincroniza la lista completa (idempotente). El backend valida coherencia
órgano↔representante↔cargo.

## Campos clínicos — `clinical-field-registrations`

> **Cambio 2026-09-02:** Ya NO existe `conventions/{id}/campos-clinicos/`. Los campos clínicos
> son CRUD independiente en `/clinical-field-registrations/` (escritura solo `CONAPRES`).

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/clinical-field-registrations/` | filtros: `convenio`, `ipress`, `carrera_profesional`, `especialidad` |
| POST | `/clinical-field-registrations/` | escritura solo `CONAPRES` |
| PATCH | `/clinical-field-registrations/{id}/` | actualizar |
| DELETE | `/clinical-field-registrations/{id}/` | eliminar |
| POST | `/clinical-field-registrations/{id}/annex-upload/` | adjuntar PDF resolución CONAPRES |
| GET | `/clinical-field-registrations/{id}/annex-checklist/` | checklist de anexos |

### ClinicalFieldRegistration — lectura
```
id, convenio, ipress, carrera_profesional, especialidad,
campos_clinicos_registrados, campos_clinicos_asignados, disponibilidad (calculado),
numero_resolucion_conapres?, fecha_resolucion_conapres?,
convenio_detalle, ipress_detalle, carrera_profesional_detalle, especialidad_detalle,
creado_en, creado_por, actualizado_en, actualizado_por
```

### ClinicalFieldRegistration — escritura
```
convenio (req), ipress (req), carrera_profesional (req), especialidad?,
campos_clinicos_registrados (req, positivo),
numero_resolucion_conapres?, fecha_resolucion_conapres?
```

## Asignaciones — `clinical-field-allocations`

CRUD de asignación (Órgano Regional) de cupos por universidad.
Escritura: `campo_clinico_ipress` (req), `convenio` (req), `fecha_inicio` (req), `fecha_fin` (req),
`campos_clinicos_autorizados` (req). La sede/carrera/especialidad/universidad las deriva el backend.

## Adjuntos (transversal)

- `conventions/{id}/annex-upload` / `annex-checklist` → actor `CONVENIO` (resoluciones: `RESOL_MARCO`, `RESOL_ESPECIFICO`, `RESOL_ADENDA`).
- `clinical-field-registrations/{id}/annex-upload` / `annex-checklist` → actor `CAMPO_CLINICO` (`RESOL_CONAPRES`).

## Otros recursos núcleo

- `convention-templates` — CRUD plantillas (escritura solo `Administrador RENADS`).
- `organ-representatives` — CRUD representantes (FK directa a `organo_directorio`). Escritura solo `Administrador RENADS`. Alta desencadena baja automática del representante anterior del mismo par `(organo_directorio, cargo_ejecutivo)`. Ver `docs/api-catalogos.md §3` para contrato completo.
- `ubigeos` — catálogo INEI (solo lectura). Filtros: `departamento`, `provincia`, `distrito`, `activo`.

## Entidades organizacionales / académicas (CRUD, escritura solo `Administrador RENADS`)

`regional-governments`, `organ-directories` (directorio unificado, discriminado por **FK `organo`**→`organs`;
filtrar `?organo=<id>`; mig 0039), `executing-units` (FK `ambito_geografico_sanitario`; mig 0043-0045),
`ipress`, `conapres`, `universities`, `faculties`, `professional-careers`, `university-campuses`,
`university-careers`, `user-entity-profiles` (solo `Administrador RENADS`, sin lectura abierta).

> **Eliminados del backend (no usar):** `regional-organs`, `minsa-organs`, `university-authorities`,
> `organ-types`. Usar `organ-directories?categoria=<VALOR>` según corresponda.
> Contrato detallado por entidad en `docs/api-catalogos.md §2`.

## Catálogos (solo lectura — `list`/`retrieve`, filtro `activo`, search `codigo`/`nombre`)

`regions`, `health-geographic-scopes`, `convention-types`, `convention-statuses`,
`university-management-types`, `authorization-types`, `academic-levels`,
`specialties`, `signing-authority-types`,
`identity-document-types`, `executive-positions`, `observation-reasons`, `rejection-reasons`,
`closure-reasons`, `organs` (5 categorías canónicas, solo lectura).

> **Eliminados del backend (no usar):** `document-types`, `university-entity-types`,
> `regional-organ-types`, `minsa-organ-types`, `executing-unit-types`, `organ-types`.

> Los `estado_codigo` de convenios provienen del catálogo `convention-statuses`.
> Cargarlo para etiquetas y transiciones; no hardcodear nombres.
