# Guía de pruebas manuales — Directorio de órganos, representantes y gestión documental

> Cubre los endpoints nuevos/renombrados de la reorganización: `organ-directories`,
> `executive-positions` (ahora CRUD), `organ-representatives`, `organ-representative-history`
> y el flujo documental (`documents`, `annex-upload`). Valida además que los endpoints
> retirados devuelven 404.
>
> **QA puede seguir esta guía sin leer el código.** Todas las llamadas asumen un cliente
> HTTP (curl/Postman/Insomnia) o el Swagger interactivo.

---

## 1. Prerrequisitos

1. Levantar el servidor (lo corre el usuario, no QA):
   ```
   .venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger (alternativa interactiva):** `http://localhost:8000/api/v1/docs/`
4. **Obtener token JWT** (usuario/contraseña de un `Administrador RENADS` o superusuario):
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "admin", "password": "<tu-password>" }
   ```
   Respuesta `200`: `{ "access": "<jwt>", "refresh": "<jwt>" }`.
   En todas las llamadas siguientes enviar el header:
   ```
   Authorization: Bearer <access>
   ```
5. **Rol/permiso por endpoint:**
   - `organ-directories`, `executive-positions`, `organ-representatives` (escritura): grupo **`Administrador RENADS`** (o superusuario). Lectura: cualquier autenticado.
   - `organ-representative-history`: solo lectura, cualquier autenticado.
   - `documents` / `documents/upload/`: cualquier miembro institucional autenticado (`IsInstitutionalMember`).

---

## 2. Datos previos necesarios

El seed de migraciones (`0002_seed_catalogos` + reseed de `0019`) ya deja disponibles:

- **Órganos** (`GET /api/v1/organs/`): `Universidad`, `Órgano Regional`, `Órgano del MINSA`, `Unidad Ejecutora`.
- **Cargos ejecutivos** (`GET /api/v1/executive-positions/`): Rector/Vicerrector/Decano/Secretario General (Universidad); Director General/Gerente General/… (Órgano Regional); Ministro/Viceministro/… (Órgano del MINSA).
- **Tipos de documento de identidad** (`GET /api/v1/identity-document-types/`): p. ej. `DNI`.
- **Anexos** (`GET /api/v1/annex-documents/?tipo_actor=REPRESENTANTE`): resolución del cargo, documento de identidad. Los genéricos (`ANEXO`/`CONVENIO`/`RESOLUCION`) tienen `tipo_actor` vacío.

Anota los `id` de: un `organo` de categoría **Universidad**, un `cargo_ejecutivo` cuyo `organo` sea el mismo, un `tipo_documento_identidad`, y un `documento_anexo` con `tipo_actor="REPRESENTANTE"`.

> Si un catálogo está vacío, créalo primero vía su endpoint CRUD (solo `Administrador RENADS`).

---

## 3. Flujo paso a paso

### Paso 3.1 — Listar cargos ejecutivos filtrando por órgano (T1 / T25)

```
GET /api/v1/executive-positions/?organo=<ID_ORGANO_UNIVERSIDAD>
```
**Esperado `200`:** lista de cargos (Rector, Decano, …) todos con `"organo": <ID_ORGANO_UNIVERSIDAD>`.
Guarda un `id` de cargo → `CARGO_ID`.

Verifica que es CRUD (crear un cargo nuevo):
```
POST /api/v1/executive-positions/
Content-Type: application/json

{ "organo": <ID_ORGANO_UNIVERSIDAD>, "codigo": "COORD_ACAD", "nombre": "Coordinador Académico", "activo": true }
```
**Esperado `201`.** Repetir el mismo `POST` con el mismo `(organo, codigo)` → **`400`** por `unique_together (organo, codigo)`.

### Paso 3.2 — Crear un órgano del directorio (T2 / T25)

```
POST /api/v1/organ-directories/
Content-Type: application/json

{
  "organo": <ID_ORGANO_UNIVERSIDAD>,
  "tipo_organo": null,
  "gobierno_regional": null,
  "nombre": "Universidad Nacional Mayor de San Marcos",
  "siglas": "UNMSM",
  "direccion": "Av. Universitaria s/n",
  "numero_ruc": "20148092282",
  "correo": "contacto@unmsm.edu.pe",
  "telefono_institucional": "016197000",
  "activo": true
}
```
**Esperado `201`** con `id`. Guarda → `DIRECTORIO_ID`.
Filtro: `GET /api/v1/organ-directories/?organo=<ID_ORGANO_UNIVERSIDAD>` → incluye el creado.
Logo (opcional): `POST /api/v1/organ-directories/<DIRECTORIO_ID>/upload-logo/` (multipart, campo `archivo`, imagen PNG/JPEG/WEBP) → `200` con `{ referencia_logo, url }`.

### Paso 3.3 — Registrar el primer representante «A» (T7 / T13 / T22)

```
POST /api/v1/organ-representatives/
Content-Type: application/json

{
  "organo_directorio": <DIRECTORIO_ID>,
  "nombre": "Ana Pérez",
  "tipo_documento_identidad": <ID_DNI>,
  "numero_documento_identidad": "11111111",
  "sexo": "F",
  "cargo_ejecutivo": <CARGO_ID>,
  "fecha_inicio_designacion": "2025-01-01",
  "numero_resolucion_designacion": "R-001-2025",
  "fecha_inicio_facultades": null
}
```
**Esperado `201`** con `"activo": true`. Guarda → `REP_A_ID`.

> **Nota de coherencia (T17):** `cargo_ejecutivo.organo` debe coincidir con `organo_directorio.organo`. Si envías un cargo de otro órgano → **`400`** `"El cargo ejecutivo no corresponde al órgano del directorio."`.

### Paso 3.4 — Designar un nuevo representante «B» para el mismo par → dispara el histórico (RN T13)

Mismo `(organo_directorio, cargo_ejecutivo)` que A, con distinto documento:
```
POST /api/v1/organ-representatives/
Content-Type: application/json

{
  "organo_directorio": <DIRECTORIO_ID>,
  "nombre": "Bruno Quispe",
  "tipo_documento_identidad": <ID_DNI>,
  "numero_documento_identidad": "22222222",
  "sexo": "M",
  "cargo_ejecutivo": <CARGO_ID>,
  "fecha_inicio_designacion": "2025-06-01",
  "numero_resolucion_designacion": "R-045-2025",
  "fecha_inicio_facultades": null,
  "motivo": "Cambio de autoridad"
}
```
**Esperado `201`** con `"activo": true` (B). Como efecto de la RN:
- `GET /api/v1/organ-representatives/<REP_A_ID>/` → **`"activo": false`** (A dado de baja).
- `GET /api/v1/organ-representative-history/?organo_directorio=<DIRECTORIO_ID>` → **una fila** con `representante=REP_A_ID`, `nombre="Ana Pérez"` (snapshot), `fecha_baja` = fecha de hoy, `motivo="Cambio de autoridad"`.

### Paso 3.5 — Adjuntar el PDF de un anexo del representante (actor REPRESENTANTE) (T21)

```
POST /api/v1/organ-representatives/<REP_B_ID>/annex-upload/
Content-Type: multipart/form-data

documento_anexo = <ID_ANEXO_REPRESENTANTE>
archivo = <archivo.pdf>
```
**Esperado `201`** con el `Document` creado: incluye `documento_anexo`, `version: 1`, `estado: "ACTIVO"`, `referencia_externa`; **no** existen campos `nombre_archivo` ni `texto_extraido`.
Subir de nuevo el mismo `documento_anexo` para el mismo representante → `201` con `version: 2` (el anterior pasa a `REEMPLAZADO`).

Checklist:
```
GET /api/v1/organ-representatives/<REP_B_ID>/annex-checklist/
```
**Esperado `200`:** lista de anexos `REPRESENTANTE` con `adjuntado: true` para el subido.

### Paso 3.6 — Gestión documental genérica por `documento_anexo` (T15 / T26)

Subida directa a cualquier objeto (relación genérica):
```
POST /api/v1/documents/upload/
Content-Type: multipart/form-data

tipo_contenido = <ID_CONTENTTYPE_DESTINO>
id_objeto = <ID_OBJETO_DESTINO>
documento_anexo = <ID_ANEXO>
archivo = <archivo.pdf>
```
**Esperado `201`** con `documento_anexo` poblado. Filtro:
```
GET /api/v1/documents/?documento_anexo=<ID_ANEXO>&estado=ACTIVO
```
**Esperado `200`** con el documento. (El filtro `tipo_documento` ya no existe.)

---

## 4. Casos de regla de negocio que DEBEN fallar

| # | Acción | Resultado esperado |
|---|--------|--------------------|
| RN-U1 | `POST /api/v1/executive-positions/` repitiendo `(organo, codigo)` existente | **`400`** (unicidad `unique_together`) |
| RN-D1 | `POST /api/v1/organ-representatives/` con `numero_documento_identidad` de un representante **activo** existente (mismo `tipo_documento_identidad`) | **`400`** `"Ya existe un representante activo con ese documento."` |
| RN-D2 | `POST /api/v1/organ-representatives/` con `cargo_ejecutivo` cuyo `organo` ≠ `organo_directorio.organo` | **`400`** `"El cargo ejecutivo no corresponde al órgano del directorio."` |
| RN-A1 | `POST /api/v1/organ-representatives/<id>/annex-upload/` con un `documento_anexo` cuyo `tipo_actor` ≠ `REPRESENTANTE` (p. ej. uno de `INTERNO`) | **`400`** `"El anexo seleccionado no corresponde a este tipo de actor."` |
| RN-A2 | `annex-upload` con un archivo que **no** sea PDF (`.png`, `.docx`) | **`400`** (tipo de archivo no permitido) |
| RN-P1 | Cualquier `POST`/`PUT`/`DELETE` en `organ-directories`/`executive-positions`/`organ-representatives` con un usuario **sin** grupo `Administrador RENADS` | **`403`** |
| RN-H1 | Cualquier `POST`/`PUT`/`DELETE` en `organ-representative-history` | **`405`** (read-only) |

---

## 5. Endpoints retirados (deben responder 404)

Confirmar que ya no existen (con token válido, para descartar 401):

```
GET /api/v1/regional-organs/         → 404
GET /api/v1/minsa-organs/            → 404
GET /api/v1/university-authorities/  → 404
GET /api/v1/representatives/         → 404
GET /api/v1/document-types/          → 404
```

---

## 6. Regresión: flujo de declaraciones juradas del interno (T16)

El renombre de tablas no debe romper el flujo del interno:
1. `POST /api/v1/interns/<id>/annex-upload/` (actor `INTERNO`, un PDF de DJ obligatoria) → `201`.
2. Al completar todas las DJ obligatorias, `GET /api/v1/interns/<id>/` muestra `estado_declaraciones` avanzando de `PENDIENTE` a `COMPLETAS`.
3. `GET /api/v1/interns/<id>/annex-checklist/` refleja `adjuntado: true` para las DJ subidas.

**Esperado:** sin errores 500; el versionado y el checklist operan sobre `documento_anexo`/`documento_adjunto`.
