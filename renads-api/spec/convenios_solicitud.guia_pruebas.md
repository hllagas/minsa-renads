# Guía de pruebas manuales — Mejora del Registro de Solicitud de Convenios

Cubre los endpoints nuevos de las Fases A y C: **partes firmantes** (`conventions/{id}/parties`), **nomenclatura** (gate en `evaluacion-tecnica`), **resolución de facultades** del representante, y **generación de PDF** (`generar-proyecto`, `generar-expediente`). La Fase B (Cloudflare R2) no expone endpoints propios: se ejerce indirectamente al subir los PDFs generados (con `R2_ENABLED=True`) o vía el stub (`R2_ENABLED=False`, default en dev).

> QA puede seguir esta guía sin leer código. Todas las rutas cuelgan de la URL base y requieren token salvo la obtención del token.

---

## 1. Prerrequisitos

1. El **usuario** levanta el servidor (no lo corre QA):
   ```
   .venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger (alternativa interactiva):** `http://localhost:8000/api/v1/docs/`
4. **Obtener token JWT:**
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "<usuario>", "password": "<contraseña>" }
   ```
   Respuesta `200`: `{ "access": "<jwt>", "refresh": "<jwt>", ... }`.
   En todas las llamadas siguientes enviar la cabecera:
   ```
   Authorization: Bearer <access>
   ```
5. **Para generar PDF** (Fase C, paso 6): el servidor necesita **LibreOffice** (`soffice` en el PATH). Sin él, `generar-proyecto`/`generar-expediente` responden `500` con mensaje en español ("LibreOffice (soffice) no está disponible en el PATH…"). Para probar la subida a R2, `R2_ENABLED=True` y credenciales R2 válidas en `.env`; en dev con `R2_ENABLED=False` el binario se registra vía stub.

### Roles requeridos por endpoint

| Endpoint | Rol/grupo requerido (escritura) |
|---|---|
| `POST /conventions/` | Miembro institucional con alcance sobre la entidad solicitante |
| `POST /conventions/{id}/parties/` | Miembro institucional con alcance del convenio + módulo en ventana (`IsModuleEnabled`) |
| `POST /conventions/{id}/evaluacion-tecnica/` | `DIGEP` |
| `POST /organ-representatives/` | `Administrador RENADS` |
| `POST /conventions/{id}/generar-proyecto/` | Miembro institucional con alcance del convenio + `IsModuleEnabled` |
| `POST /conventions/{id}/generar-expediente/` | Miembro institucional con alcance del convenio + `IsModuleEnabled` |

> Lectura (`GET`) siempre disponible para autenticados con alcance. Superusuario y `Administrador RENADS` están exentos del gate temporal `IsModuleEnabled`.

---

## 2. Datos previos necesarios

Deben existir (ya seedeados o creados por API con rol `Administrador RENADS`):

- Catálogos base seedeados: `convention-types` (MARCO/ESPECIFICO), `convention-statuses` (incluye `SOLICITUD_REGISTRADA`, `VALIDADO_TECNICAMENTE`), tipos de documento de identidad, `executive-positions`.
- Un **órgano del directorio** (`GET /organ-directories/`) por categoría según el caso:
  - Marco región: uno `GOBIERNO_REGIONAL` (con `gobierno_regional` asociado).
  - Marco Lima: uno `MINSA_DIRIS`.
  - Uno de categoría `UNIVERSIDAD` (para la parte UNIVERSIDAD).
- Una **universidad** (`GET /universities/`), su **facultad** (`GET /faculties/`) y, para el Específico, una **unidad ejecutora** (`GET /executing-units/`).
- Al menos un **cargo ejecutivo** (`GET /executive-positions/`) perteneciente a cada órgano del directorio que se use en las partes (coherencia `cargo.organo_directivo == organo_directorio`).
- Los `documento_anexo` de generación (`PROYECTO_CONVENIO`, `PROYECTO_ADENDA`, `EXPEDIENTE`) — se crean con la migración `internados/0020`; verificables en `GET /annex-documents/?tipo_actor=CONVENIO`.

Recuperar los `id` de estas entidades vía `GET` antes de armar los payloads.

---

## 3. Flujo paso a paso

### Paso 1 — Crear un representante con resolución de facultades (Fase A2)

Rol: `Administrador RENADS`.

```
POST /api/v1/organ-representatives/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo_directorio": 3,
  "nombre": "María Pérez Rojas",
  "tipo_documento_identidad": 1,
  "numero_documento_identidad": "40123456",
  "sexo": "F",
  "cargo_ejecutivo": 5,
  "fecha_inicio_designacion": "2026-01-15",
  "numero_resolucion_designacion": "RD-100-2026",
  "numero_resolucion_facultades": "RF-200-2026",
  "fecha_inicio_facultades": "2026-01-20"
}
```

Esperado `201`. La respuesta incluye `numero_resolucion_facultades`. Guardar el `id` (p. ej. `12`).
Repetir para el representante de la universidad (`organo_directorio` de categoría UNIVERSIDAD, su cargo).

> Regla del histórico: si se registra otro representante para el mismo `(organo_directorio, cargo_ejecutivo)`, el anterior se da de baja; verificarlo con `GET /organ-representative-history/?organo_directorio=3` (el snapshot conserva `numero_resolucion_facultades`).

### Paso 2 — Crear un Convenio Marco (región)

Rol: miembro institucional con alcance sobre el órgano solicitante.

```
POST /api/v1/conventions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_convenio": 1,
  "titulo": "Convenio Marco GERESA X - Universidad Y",
  "solicitante_tipo_contenido": 45,
  "solicitante_id_objeto": 3,
  "organo_directorio": 3,
  "universidad": 2,
  "fecha_solicitud": "2026-09-01"
}
```

(`tipo_convenio=1` = MARCO; `organo_directorio` categoría `GOBIERNO_REGIONAL`; sin `unidad_ejecutora`/`facultad`.)
Esperado `201`. La respuesta (read serializer) incluye `nomenclatura` (vacía) y `partes_firmantes` (`[]`). Guardar `id` (p. ej. `20`).

### Paso 3 — Sincronizar las partes firmantes (Fase A6)

Rol: miembro institucional con alcance del convenio. Marco región requiere roles `MINSA` + `GOBIERNO_REGIONAL` + `UNIVERSIDAD`.

```
POST /api/v1/conventions/20/parties/
Authorization: Bearer <access>
Content-Type: application/json

[
  { "rol": "MINSA", "organo_directorio": 1, "orden": 1, "es_firmante": true },
  { "rol": "GOBIERNO_REGIONAL", "organo_directorio": 3, "organo_representante": 12, "cargo_ejecutivo": 5, "orden": 1, "es_firmante": true },
  { "rol": "UNIVERSIDAD", "organo_directorio": 7, "organo_representante": 13, "cargo_ejecutivo": 9, "orden": 1, "es_firmante": true }
]
```

Esperado `200`: lista de partes con `rol_display`, `organo_directorio_detalle`, `organo_representante_detalle`, `cargo_ejecutivo_detalle`.

Verificar idempotencia: reenviar el mismo payload → misma cantidad de partes (no duplica).
Verificar lectura embebida: `GET /api/v1/conventions/20/` → `partes_firmantes` con las 3 partes.
Verificar listado dedicado: `GET /api/v1/conventions/20/parties/` → mismas 3 partes.

### Paso 4 — Aprobar validación técnica (DIGEP) asignando la nomenclatura (Fase A3)

Rol: `DIGEP`.

```
POST /api/v1/conventions/20/evaluacion-tecnica/
Authorization: Bearer <access>
Content-Type: application/json

{
  "resultado": "VALIDADO",
  "observaciones": "",
  "fecha_evaluacion": "2026-09-02",
  "nomenclatura": "CONV-MARCO-036-2026-MINSA"
}
```

Esperado `200`: la respuesta muestra `estado_codigo = "VALIDADO_TECNICAMENTE"` y `nomenclatura = "CONV-MARCO-036-2026-MINSA"`.

Verificar que `nomenclatura` NO se edita por PATCH libre:
```
PATCH /api/v1/conventions/20/   { "nomenclatura": "HACK-999" }
```
Esperado `200` pero `nomenclatura` **no cambia** (el campo no está en el write serializer).

### Paso 5 — Generar el proyecto de convenio en PDF (Fase C4)

Rol: miembro institucional con alcance del convenio. Requiere LibreOffice en el servidor.

```
POST /api/v1/conventions/20/generar-proyecto/
Authorization: Bearer <access>
```

Esperado `201`: un `documento_adjunto` con `documento_anexo_nombre = "Proyecto de convenio (PDF generado)"`, `version = 1`, `estado = "ACTIVO"`.
Repetir la llamada → nuevo documento `version = 2`; el anterior queda `REEMPLAZADO` (verificable con `GET /api/v1/documents/?tipo_contenido=<ct_convention>&id_objeto=20`).
Descargar el binario: `GET /api/v1/documents/{doc_id}/url-descarga/` → `{ "url": "<presigned/stub>" }`.

### Paso 6 — Generar el expediente consolidado (Fase C4)

```
POST /api/v1/conventions/20/generar-expediente/
Authorization: Bearer <access>
```

Esperado `201`: un `documento_adjunto` con `documento_anexo_nombre = "Expediente del convenio (PDF consolidado)"`. El PDF concatena el proyecto + las resoluciones adjuntas de los representantes firmantes (si existen); los adjuntos faltantes se omiten sin fallar.

### Paso 7 (opcional) — Convenio Específico + adenda

- Crear un **Específico** (`tipo_convenio` = ESPECIFICO) enviando además `convenio_marco` (id del Marco vigente), `unidad_ejecutora` y `facultad` (la facultad debe pertenecer a la universidad del Marco).
- Sincronizar partes con roles `UNIDAD_EJECUTORA` + `FACULTAD`.
- `POST /conventions/{id}/generar-proyecto/` usa la plantilla Específico (Lima/región según categoría).
- Crear una adenda: `POST /conventions/{id}/adenda/` con `{ "fecha_inicio": "2027-01-01" }`; su `generar-proyecto` usa la plantilla `adenda.docx` y el anexo `PROYECTO_ADENDA`.

---

## 4. Casos de regla de negocio que deben fallar

### RN — Composición de partes por tipo/categoría (Fase A4.2)

Marco región al que le falta el rol `MINSA`:
```
POST /api/v1/conventions/20/parties/
[
  { "rol": "GOBIERNO_REGIONAL", "organo_directorio": 3, "orden": 1 },
  { "rol": "UNIVERSIDAD", "organo_directorio": 7, "orden": 1 }
]
```
Esperado `400`: "Faltan las partes requeridas para este tipo de convenio: MINSA."

### RN — Coherencia órgano ↔ representante (Fase A4.1)

Representante que no pertenece al órgano de la parte:
```
POST /api/v1/conventions/20/parties/
[ { "rol": "GOBIERNO_REGIONAL", "organo_directorio": 3, "organo_representante": 99, "orden": 1 } ]
```
(donde el representante `99` pertenece a otro `organo_directorio`.)
Esperado `400`: "El representante no pertenece al órgano del directorio indicado."

### RN — Coherencia cargo ↔ órgano (Fase A4.1)

Cargo cuyo `organo_directivo` no coincide con `organo_directorio` de la parte → `400`: "El cargo no pertenece al órgano del directorio indicado."

### RN — Nomenclatura solo Marco, requerida al validar (Fase A3)

a) Marco validado **sin** nomenclatura:
```
POST /api/v1/conventions/20/evaluacion-tecnica/
{ "resultado": "VALIDADO", "fecha_evaluacion": "2026-09-02" }
```
Esperado `400`: `{"nomenclatura": "Requerida para aprobar la validación técnica del Marco."}`.

b) **Específico** validado con `nomenclatura` → se **ignora** (no la exige ni la asigna); la evaluación procede con `200`. Confirmar que `GET` del Específico mantiene `nomenclatura` vacía.

### RN — Alcance institucional / permiso de rol

- `evaluacion-tecnica` con un usuario sin rol `DIGEP` → `403`.
- `organ-representatives` `POST` con usuario sin `Administrador RENADS` → `403`.
- `parties`/`generar-*` con un usuario sin alcance sobre el convenio → `403`/`404` (fuera de `convenios_visibles`).

### RN — Gate temporal del módulo (calendario, `IsModuleEnabled`)

Si existe una `CalendarActivity` que gobierna `convenios.convention` con la ventana **fuera de fechas**, un usuario **no** exento (ni superusuario ni `Administrador RENADS`) recibe en `parties`/`generar-*`:
Esperado `403` con `code = "MODULO_FUERA_DE_VENTANA"`. Consultar el estado en `GET /api/v1/auth/me/` (`modulos_bloqueados`).

---

## 5. Verificación de auditoría (transversal)

Tras los pasos 1-6, con rol `Administrador RENADS`/`Auditor`:
```
GET /api/v1/audit-logs/?id_objeto=20
```
Deben aparecer entradas `CREAR`/`ACTUALIZAR`/`ELIMINAR`/`CAMBIO_ESTADO` para el convenio, sus partes, la nomenclatura y los documentos generados.
