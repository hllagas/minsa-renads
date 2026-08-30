# Guía de pruebas manuales — Flujo de convenios (Marco → Específico → campos clínicos → adenda → suscripción)

Guía end-to-end para QA. Cubre los endpoints/campos **nuevos** de la mejora del flujo de
convenios y valida las reglas de negocio con casos que **deben fallar**. Los `id` de una
respuesta alimentan el paso siguiente.

## 0. Prerrequisitos

1. El **usuario** levanta el servidor: `python manage.py runserver`.
2. URL base: `http://localhost:8000/api/v1/`.
3. Alternativa interactiva: Swagger UI en `http://localhost:8000/api/v1/docs/`.
4. Obtener token JWT:

```
POST /api/v1/auth/token/
Content-Type: application/json

{ "username": "<usuario>", "password": "<contraseña>" }
```

Respuesta `200`: `{ "access": "...", "refresh": "..." }`. En todas las llamadas siguientes:
`Authorization: Bearer <access>`.

### Roles por endpoint

| Acción | Grupo/rol requerido |
|---|---|
| Crear/editar convenio, crear adenda | rol de la **entidad solicitante** (alcance por `perfil_usuario_entidad`) |
| `conventions/{id}/cambiar-estado`, `participantes` | `Administrador RENADS` |
| `conventions/{id}/evaluacion-tecnica` | `DIGEP` |
| `conventions/{id}/opinion-conapres` | `CONAPRES` |
| `conventions/{id}/opinion-juridica` | `OGAJ` |
| `conventions/{id}/firma`, `publicacion` | `Secretaría General` |
| `clinical-field-registrations/` (escritura) | `CONAPRES` (`IsConapresOrReadOnly`) |
| `clinical-field-allocations/` (escritura) | grupo `Gobierno Regional` |
| `annex-upload` / `annex-checklist` | mismo permiso del ViewSet padre |

> Nota: el módulo de convenios está gobernado por el Calendario (`IsModuleEnabled`). Si las
> escrituras devuelven `403 MODULO_FUERA_DE_VENTANA`, use un usuario superusuario o
> `Administrador RENADS`, o cree una ventana vigente en `calendar-activities/` para el
> ContentType `convenios.convention`.

## 1. Datos previos necesarios (deben existir / seedearse)

- Catálogos seedeados: `ConventionType` (`MARCO`/`ESPECIFICO`), `ConventionStatus` (26
  estados), `documento_anexo` (incluye ya `RESOL_MARCO`/`RESOL_ESPECIFICO`/`RESOL_ADENDA`
  con `tipo_actor=CONVENIO` y `RESOL_CONAPRES` con `tipo_actor=CAMPO_CLINICO`).
- `organs` / `organ-directories` con un órgano `GERESA` o `DIRESA` (para el Marco).
- `universities` (universidad) y al menos una `faculty` **de esa universidad**.
- `executing-units` (unidad ejecutora) asociada a la región.
- `ipress` con `es_sede_docente=true` **y** `unidad_ejecutora` = la del convenio específico.
- `professional-careers` (carrera profesional).
- El `content_type` id del solicitante (`GET /api/v1/content-types/` o
  `GET /api/v1/convention-solicitante-types/` según el proyecto) para
  `solicitante_tipo_contenido`.

## 2. Crear Convenio Marco (rol GERESA/DIRESA)

```
POST /api/v1/conventions/
{
  "tipo_convenio": <id_tipo_MARCO>,
  "titulo": "Convenio Marco GERESA X - Universidad Y",
  "solicitante_tipo_contenido": <ct_id_organo_directorio>,
  "solicitante_id_objeto": <id_organo_directorio>,
  "organo_directorio": <id_organo_GERESA>,
  "universidad": <id_universidad>,
  "fecha_solicitud": "2026-08-30",
  "fecha_inicio": "2026-09-01"
}
```

Esperado `201`. Guardar `id` → `MARCO_ID`. Verificar en la respuesta `es_adenda=false`,
`convenio_origen=null`, `unidad_ejecutora=null`, `facultad=null`, `vigencia_efectiva` =
`fecha_fin` (derivada de `anios_vigencia` si aplica), `adendas=[]`.

### 2b. Caso que DEBE fallar — Marco con partes de Específico (RN partes por tipo)

```
POST /api/v1/conventions/     (mismo payload + )
  "unidad_ejecutora": <id_ue>,
  "facultad": <id_facultad>
```

Esperado `400`: `{"unidad_ejecutora": "Un Convenio Marco no lleva unidad ejecutora ni facultad."}`.

### 2c. Llevar el Marco a estado vigente

Avance el Marco a `VIGENTE` (o `SUSCRITO`/`PUBLICADO`) para que soporte un Específico:

```
POST /api/v1/conventions/{MARCO_ID}/cambiar-estado/     (rol Administrador RENADS)
{ "estado_codigo": "VIGENTE", "observacion": "Vigente para pruebas" }
```

## 3. Crear Convenio Específico (con Marco vigente)

```
POST /api/v1/conventions/
{
  "tipo_convenio": <id_tipo_ESPECIFICO>,
  "convenio_marco": MARCO_ID,
  "titulo": "Convenio Específico UE Z - Facultad de Medicina",
  "solicitante_tipo_contenido": <ct_id_organo_directorio>,
  "solicitante_id_objeto": <id_organo_directorio>,
  "organo_directorio": <id_organo>,
  "universidad": <id_universidad>,
  "unidad_ejecutora": <id_ue>,
  "facultad": <id_facultad_de_esa_universidad>,
  "fecha_solicitud": "2026-08-30",
  "fecha_inicio": "2026-09-01",
  "max_campos_clinicos": 50
}
```

Esperado `201`. Guardar `id` → `ESPECIFICO_ID`. Verificar `unidad_ejecutora_detalle` y
`facultad_detalle` poblados.

### Casos que DEBEN fallar

- **Sin `unidad_ejecutora`** → `400 {"unidad_ejecutora": "Requerida para un Convenio Específico."}`.
- **Sin `facultad`** → `400 {"facultad": "Requerida para un Convenio Específico."}`.
- **`facultad` de otra universidad** → `400 {"facultad": "La facultad debe pertenecer a la universidad del Convenio Marco."}`.
- **`convenio_marco` no vigente** (usar un Marco en estado inicial) → `400 {"convenio_marco": "El Convenio Marco debe estar vigente."}`.

## 4. Registrar campos clínicos con resolución CONAPRES (rol CONAPRES)

```
POST /api/v1/clinical-field-registrations/
{
  "convenio": ESPECIFICO_ID,
  "ipress": <id_ipress_sede_docente_de_la_UE>,
  "carrera_profesional": <id_carrera>,
  "campos_clinicos_registrados": 10,
  "numero_resolucion_conapres": "RES-CONAPRES-2026-001",
  "fecha_resolucion_conapres": "2026-08-20"
}
```

Esperado `201`. Guardar `id` → `REGISTRO_ID`. Verificar `disponibilidad = 10`,
`campos_clinicos_asignados = 0`, y que el Específico avanzó a `CAMPOS_CLINICOS_DEFINIDOS`
(GET del convenio → `estado_codigo`).

### Casos que DEBEN fallar

- **`ipress` sin `es_sede_docente`** → `400 {"ipress": "La IPRESS debe estar autorizada como sede docente por CONAPRES."}`.
- **`ipress` de otra unidad ejecutora** (≠ `convenio.unidad_ejecutora`) →
  `400 {"ipress": "La sede docente debe pertenecer a la unidad ejecutora del Convenio Específico."}`.

### 4b. Adjuntar la resolución CONAPRES en PDF (actor CAMPO_CLINICO)

```
GET /api/v1/clinical-field-registrations/{REGISTRO_ID}/annex-checklist/
```
Debe listar `RESOL_CONAPRES` con `adjuntado=false`. Luego:

```
POST /api/v1/clinical-field-registrations/{REGISTRO_ID}/annex-upload/
Content-Type: multipart/form-data
  documento_anexo = <id_RESOL_CONAPRES>
  archivo = @resolucion.pdf
```
Esperado `201` con el `Document` versionado. `annex-checklist` ahora muestra `adjuntado=true`.

- **Caso que DEBE fallar**: subir un anexo de `tipo_actor` distinto (p. ej. `RESOL_MARCO`,
  actor `CONVENIO`) por este endpoint → `400 {"documento_anexo": "El anexo seleccionado no corresponde a este tipo de actor."}`.

## 5. Gate de suscripción — requisito de campos clínicos con resolución

### 5a. Caso que DEBE fallar (sin resolución) — probar ANTES del paso 4

Con un Específico **sin** ningún `campo_clinico_ipress` con `numero_resolucion_conapres`,
intentar avanzar a suscripción:

```
POST /api/v1/conventions/{ESPECIFICO_ID}/cambiar-estado/
{ "estado_codigo": "ENVIADO_SG" }
```
Esperado `400`: `"No se puede avanzar a suscripción: falta al menos un campo clínico
registrado por CONAPRES (con resolución) sobre una sede docente de la unidad ejecutora."`.

El mismo mensaje aplica al registrar la firma:
```
POST /api/v1/conventions/{ESPECIFICO_ID}/firma/     (rol Secretaría General)
```

### 5b. Con el registro del paso 4 presente → procede

Repetir `ENVIADO_SG` (o `firma`) tras el paso 4 → ya no bloquea. Continuar el flujo hasta
`VIGENTE` (`cambiar-estado`), para poder ampliarlo con una adenda.

## 6. Crear una adenda (nuevo periodo) del Específico

```
POST /api/v1/conventions/{ESPECIFICO_ID}/adenda/
{
  "titulo": "Adenda de ampliación 2027",
  "fecha_inicio": "2027-09-01",
  "fecha_fin": "2028-08-31"
}
```

Esperado `201`. Guardar `id` → `ADENDA_ID`. Verificar `es_adenda=true`,
`convenio_origen = ESPECIFICO_ID`, y que hereda `tipo_convenio`, `unidad_ejecutora`,
`facultad` del origen; estado inicial `SOLICITUD_REGISTRADA`.

- **Caso que DEBE fallar**: omitir `fecha_inicio` → `400 {"fecha_inicio": "Requerida para crear una adenda."}`.
- **Caso que DEBE fallar**: `fecha_fin <= fecha_inicio` → `400 {"fecha_fin": "Debe ser posterior a la fecha de inicio."}`.

### 6b. Pasar la adenda a VIGENTE → el origen queda AMPLIADO

Lleve la adenda hasta `VIGENTE` (`cambiar-estado`, misma secuencia que un convenio). Al
alcanzar `VIGENTE`:

- `GET /api/v1/conventions/{ESPECIFICO_ID}/` → `estado_codigo = "AMPLIADO"`.
- El campo `vigencia_efectiva` del origen = `fecha_fin` de la adenda (`2028-08-31`).
- El campo `adendas` del origen lista la adenda con su estado.

### 6c. Cadena de 2+ adendas (sin límite)

```
POST /api/v1/conventions/{ADENDA_ID}/adenda/
{ "fecha_inicio": "2028-09-01", "fecha_fin": "2029-08-31" }
```
Esperado `201` (adenda de adenda). `vigencia_efectiva(ESPECIFICO_ID)` refleja la mayor
`fecha_fin` vigente de la cadena una vez esta segunda adenda esté `VIGENTE`.

## 7. Adjuntar resoluciones PDF del convenio (actor CONVENIO)

```
GET  /api/v1/conventions/{ESPECIFICO_ID}/annex-checklist/
```
Lista `RESOL_MARCO`/`RESOL_ESPECIFICO`/`RESOL_ADENDA` (actor `CONVENIO`).

```
POST /api/v1/conventions/{ESPECIFICO_ID}/annex-upload/
Content-Type: multipart/form-data
  documento_anexo = <id_RESOL_ESPECIFICO>
  archivo = @resolucion_especifico.pdf
```
Esperado `201` (Document versionado por `(convenio, documento_anexo)`). `annex-checklist`
refleja `adjuntado=true`. Subir de nuevo el mismo anexo genera una nueva versión.

- **Caso que DEBE fallar**: `documento_anexo = <id_RESOL_CONAPRES>` (actor `CAMPO_CLINICO`)
  por este endpoint → `400` por `tipo_actor` no correspondiente.

## 8. Filtros y lectura

- `GET /api/v1/conventions/?es_adenda=true` → solo adendas.
- `GET /api/v1/conventions/?convenio_origen={ESPECIFICO_ID}` → adendas directas del origen.
- `GET /api/v1/conventions/?convenio_marco={MARCO_ID}` → específicos del Marco.
- `GET /api/v1/conventions/{ESPECIFICO_ID}/` expone `unidad_ejecutora_detalle`,
  `facultad_detalle`, `adendas`, `vigencia_efectiva`.

## Resumen de encadenamiento de ids

`MARCO_ID` (paso 2) → `convenio_marco` del Específico (paso 3) → `ESPECIFICO_ID` →
`convenio` del registro de campo clínico (paso 4) → `REGISTRO_ID` (annex-upload paso 4b) →
gate de suscripción (paso 5) → adenda del Específico (paso 6) → `ADENDA_ID` → adenda de
adenda (paso 6c).
