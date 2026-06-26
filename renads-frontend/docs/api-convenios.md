# API — Módulo 1: Gestionar Convenios (`apps/convenios`)

Ciclo de vida de Convenios Marco y Específicos: registro, evaluación técnica (DIGEP), opinión
CONAPRES, campos clínicos, opinión jurídica (OGAJ), firma, publicación, vigencia y cierre.
Base: `/api/v1/`. Todos los endpoints requieren JWT.

## Reglas de negocio clave (para validación/UX)

- **RN-3:** un Convenio **Específico** requiere un **Convenio Marco vigente**
  (estado en `VIGENTE` / `PUBLICADO` / `SUSCRITO`).
- CONAPRES y campos clínicos **solo aplican a convenios Específicos**.
- No se puede **firmar** con observaciones pendientes (evaluación técnica / CONAPRES / OGAJ `OBSERVADO` sin subsanar).
- `fecha_fin` la calcula el backend (vigencia del tipo: 4 años Marco / 3 años Específico). No enviarla.

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
| GET·POST | `/conventions/{id}/campos-clinicos/` | POST: `CONAPRES` | GET lista, POST agrega (solo Específico) |
| POST | `/conventions/{id}/opinion-juridica/` | `OGAJ` | |
| POST | `/conventions/{id}/firma/` | `Secretaría General` | bloquea si hay observaciones pendientes |
| POST | `/conventions/{id}/publicacion/` | `Secretaría General` | `PUBLICADO` → `VIGENTE` |
| GET·POST | `/conventions/{id}/participantes/` | POST: `Administrador RENADS` | GET lista, POST agrega |
| GET | `/conventions/{id}/historial/` | autenticado | historial de estados |

**Filtros** (`ConventionFilter`): `tipo_convenio`, `estado_actual`, `convenio_marco`, rangos de
`fecha_solicitud` / `fecha_inicio` / `fecha_fin`, solicitante (tipo + id).
**Search:** `titulo`, `codigo`. **Ordering:** `fecha_solicitud`, `fecha_inicio`, `fecha_fin`, `id`.

### Convention — lectura (`GET`)
```
id, tipo_convenio, convenio_marco, plantilla, codigo, titulo,
solicitante_tipo_contenido, solicitante_id_objeto, solicitante,
estado_actual, estado_codigo, fecha_solicitud, fecha_inicio, fecha_fin,
max_campos_clinicos, creado_por, creado_en, actualizado_en
```
### Convention — escritura (`POST`/`PUT`)
```
tipo_convenio, convenio_marco, plantilla, codigo, titulo,
solicitante_tipo_contenido, solicitante_id_objeto,
fecha_solicitud, fecha_inicio, fecha_fin, max_campos_clinicos
```
> `solicitante` es polimórfico: `solicitante_tipo_contenido` (id de ContentType) + `solicitante_id_objeto`.

### Payloads de acciones de flujo
- **evaluacion-tecnica:** `resultado, observaciones, subsanacion, organo_minsa, fecha_evaluacion`
  (`resultado=VALIDADO` → `VALIDADO_TECNICAMENTE`; `OBSERVADO` → `OBSERVADO_DIGEP`).
- **opinion-conapres:** `fecha_solicitud, estado_atencion, resultado_opinion, fecha_respuesta`.
- **campos-clinicos:** `ipress, carrera_profesional, especialidad, cantidad_maxima, vigencia_inicio, vigencia_fin, ambito_geografico_sanitario, observaciones`.
- **opinion-juridica:** `fecha_envio, resultado_opinion, observaciones_legales, subsanacion, fecha_respuesta`.
- **firma:** `firmante_tipo_contenido, firmante_id_objeto, tipo_autoridad_firmante, orden_firma, fecha_envio, fecha_recepcion, estado_firma, observaciones`.
- **publicacion:** `fecha_publicacion, referencia_publicacion`.
- **participantes:** `tipo_contenido, id_objeto, tipo_autoridad_firmante, es_firmante`.
- **cambiar-estado** / historial usan `{ estado_codigo, observacion? }` y devuelven el historial.

## Otros recursos núcleo

- `convention-templates` — CRUD plantillas (escritura solo `Administrador RENADS`).
- `representatives` — CRUD representantes (polimórfico: órgano MINSA / órgano regional / unidad ejecutora / IPRESS / CONAPRES). Escritura solo `Administrador RENADS`.
- `ubigeos` — catálogo INEI (solo lectura). Filtros: `departamento`, `provincia`, `distrito`, `activo`.

## Entidades organizacionales / académicas (CRUD, escritura solo `Administrador RENADS`)

`regional-governments`, `regional-organs`, `executing-units`, `ipress`, `minsa-organs`,
`conapres`, `universities`, `university-authorities`, `faculties`, `professional-careers`,
`university-campuses`, `user-entity-profiles` (esta última solo `Administrador RENADS`, sin lectura abierta).

> Cada una expone CRUD estándar con `id` + todos los campos del modelo y filtros propios
> (p. ej. `universities`: `tipo_gestion`, `tipo_entidad`, `tipo_autorizacion`, `activo`; search `nombre`, `siglas`).

## Catálogos (solo lectura — `list`/`retrieve`, filtro `activo`, search `codigo`/`nombre`)

`regions`, `health-geographic-scopes`, `convention-types`, `convention-statuses`, `document-types`,
`university-management-types`, `university-entity-types`, `authorization-types`, `academic-levels`,
`specialties`, `signing-authority-types`, `regional-organ-types`, `executing-unit-types`,
`minsa-organ-types`, `executive-positions`, `observation-reasons`, `rejection-reasons`, `closure-reasons`.

> Los `estado_codigo` de convenios (p. ej. `SOLICITUD_REGISTRADA`, `VALIDADO_TECNICAMENTE`,
> `OBSERVADO_DIGEP`, `PENDIENTE_CONAPRES`, `CONAPRES_FAVORABLE`, `CAMPOS_CLINICOS_DEFINIDOS`,
> `OGAJ_FAVORABLE`, `FIRMADO_MINSA`, `PUBLICADO`, `VIGENTE`, ...) provienen del catálogo
> `convention-statuses`. Cargarlo para etiquetas y transiciones; no hardcodear nombres.
