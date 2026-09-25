# Guía de pruebas manuales — Rename `OrganDirectory` → `OrganicUnit` (unidad orgánica)

> Módulo: **Gestionar Convenios** (`apps/convenios`) + `apps/common`.
> Tipo: refactor de rename in-place. Objetivo de QA: confirmar que el nuevo endpoint
> `organic-units` opera, que el viejo `organ-directories` responde 404, y que las reglas de
> negocio que dependen de la unidad orgánica siguen funcionando (sin cambios de comportamiento).

---

## Resultado de la validación

**VALIDACIÓN EXITOSA** — sin hallazgos altos/medios. Los 10 criterios de la §7 del spec pasan:

1. Sin residuos de `OrganDirectory|organo_directorio|organo_directivo|organ-directories` en código de app (`apps/**` excluyendo migraciones): **0 coincidencias**.
2. Modelo `OrganicUnit` con `db_table="unidad_organica"`; `OrganDirectory` no existe.
3. Las 5 FK (F1 `ExecutivePosition`, F2 `Convention`, F3 `ConventionParty`, F4 `TechnicalEvaluation`, F5 `UserProfile`) usan atributo `unidad_organica` + `db_column="unidad_organica_id"`; related_names `cargos` / `convenios` / `+` / `+` / `perfiles_usuarios` sin colisión.
4. Migración `0054_rename_organic_unit` usa solo rename/alter (sin `CreateModel`/`DeleteModel`); `common 0008` dependiente presente; `check` sin issues; `makemigrations --check` limpio; ambas aplicadas en PostgreSQL con datos preservados (14 filas en `unidad_organica`).
5. Router expone `organic-units`; `organ-directories` ausente.
6. Reglas de negocio intactas (RN-1, composición de partes, coherencia parte↔representante↔cargo, derivación del solicitante, PDF) — solo rename.
7. GFK: `SOLICITANTE_MODELS`, `REPRESENTANTE_MODELS`, `ASSIGNABLE_PROFILE_MODELS` incluyen `OrganicUnit`; ContentType `('convenios','organicunit')` resuelve.
8. Docs §5 y `CLAUDE.md` sincronizados (0 referencias viejas; `db_schema_modulo_01_convenios.md` con 31 referencias nuevas).
9. Bug latente `.categoria` preservado idéntico (`load_universidades.py:98` sigue `OrganicUnit.objects.filter(categoria="UNIVERSIDAD")`; lecturas de property en `services.py:407,929`).
10. Comandos de sanidad (`check`, `makemigrations --check`) ejecutados en verde.

---

## Prerrequisitos

1. Levantar el servidor (lo corre el usuario):

   ```
   .venv\Scripts\Activate.ps1
   python manage.py runserver
   ```

   URL base: `http://localhost:8000/api/v1/`
   Swagger interactivo (alternativa): `http://localhost:8000/api/v1/docs/`

2. Obtener token JWT:

   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "<usuario>", "password": "<contraseña>" }
   ```

   Respuesta esperada `200`:

   ```
   { "access": "<access>", "refresh": "<refresh>" }
   ```

   En las siguientes llamadas: `Authorization: Bearer <access>`.

3. Datos previos: deben existir filas de unidad orgánica (14 en la BD de trabajo). Si no,
   crearlas como `Administrador RENADS` en el paso 2 de la sección siguiente.

---

## Flujo paso a paso

### Paso 1 — El endpoint nuevo responde (lectura)

```
GET http://localhost:8000/api/v1/organic-units/
Authorization: Bearer <access>
```

- Estado esperado: `200`.
- Cuerpo: lista paginada de unidades orgánicas con al menos `{ id, nombre, ... }`.
- Anota un `id` para pasos posteriores.

### Paso 2 — El endpoint viejo NO existe (ruptura deliberada)

```
GET http://localhost:8000/api/v1/organ-directories/
Authorization: Bearer <access>
```

- Estado esperado: **`404`** (ruptura de contrato deliberada; no hay alias).

### Paso 3 — CRUD de unidad orgánica (rol `Administrador RENADS`)

Crear (solo `Administrador RENADS` o superusuario; otros roles → `403`):

```
POST http://localhost:8000/api/v1/organic-units/
Authorization: Bearer <access-admin>
Content-Type: application/json

{
  "organo": <id_organo_categoria>,
  "nombre": "DIRESA Prueba QA",
  "siglas": "DIRESA-QA",
  "activo": true
}
```

- Estado esperado: `201`; anota el `id` devuelto (`<id_uo>`).
- Regla de unicidad `(organo, nombre)`: repetir el mismo `POST` debe devolver `400`
  (mensaje de campo único).

### Paso 4 — Cargo ejecutivo referencia la unidad orgánica por `unidad_organica`

```
POST http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access-admin>
Content-Type: application/json

{
  "organo": <id_organo_categoria>,
  "unidad_organica": <id_uo>,
  "nombre_masculino": "Director QA",
  "nombre_femenino": "Directora QA"
}
```

- Estado esperado: `201`. La lectura debe exponer `unidad_organica` y su detalle.
- Filtro por unidad orgánica:

  ```
  GET http://localhost:8000/api/v1/executive-positions/?unidad_organica=<id_uo>
  ```

  Estado `200` con el cargo recién creado.
- Filtro `isnull` (cargos globales sin unidad orgánica):

  ```
  GET http://localhost:8000/api/v1/executive-positions/?unidad_organica__isnull=true
  ```

### Paso 5 — Convenio con `unidad_organica` (lectura del contrato renombrado)

```
GET http://localhost:8000/api/v1/conventions/?unidad_organica=<id_uo>
Authorization: Bearer <access>
```

- Estado `200`. En el detalle de un convenio, verificar que el read serializer expone:
  - `unidad_organica` (id)
  - `unidad_organica_nombre`
  - `tipo_unidad_organica`
  - (NO deben aparecer los campos viejos `organo_directorio`, `organo_directorio_nombre`,
    `tipo_organo_directorio`).

### Paso 6 — Evaluación técnica expone `unidad_organica_detalle`

En un convenio con evaluación técnica registrada:

```
GET http://localhost:8000/api/v1/conventions/<id_convenio>/
```

- El bloque de evaluación técnica debe exponer `unidad_organica` y `unidad_organica_detalle`
  (objeto con `nombre`/`siglas`), sin `organo_directorio_detalle`.

### Paso 7 — Content types del solicitante/representante incluyen la unidad orgánica

```
GET http://localhost:8000/api/v1/conventions/solicitante-content-types/
Authorization: Bearer <access>
```

(usar la ruta real de `SolicitanteContentTypeView` según el router)

- La respuesta debe incluir un elemento con `{ "app_label": "convenios", "model": "organicunit" }`.
- Análogamente para el endpoint de tipos de representante (`REPRESENTANTE_MODELS`): debe listar
  `organicunit`, y NO `organdirectory`.

---

## Casos de regla de negocio (deben comportarse igual que antes del rename)

### RN-1 — Solo GOBIERNO_REGIONAL / ORGANO_MINSA / UNIVERSIDAD pueden solicitar Convenio Marco

Crear un Convenio Marco con una `unidad_organica` cuya categoría NO sea de las permitidas
(p. ej. `UNIDAD_EJECUTORA`):

```
POST http://localhost:8000/api/v1/conventions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_convenio": "MARCO",
  "titulo": "Marco QA inválido",
  "unidad_organica": <id_uo_no_permitida>,
  "universidad": <id_universidad>,
  "fecha_solicitud": "2026-09-24"
}
```

- Estado esperado: `400`.
- Mensaje esperado (clave `unidad_organica`): *"Un Convenio Marco solo puede ser solicitado por
  un Gobierno Regional, el Ministerio de Salud o una Universidad."*

### Coherencia cargo↔entidad en parte firmante (D4)

Al sincronizar partes (`POST /api/v1/conventions/{id}/parties`) o crear un representante, enviar
un `cargo_ejecutivo` que tiene `unidad_organica` asignada pero con una `entidad`
(`tipo_contenido`/`id_objeto`) que NO corresponde a esa unidad orgánica:

- Estado esperado: `400`.
- Mensaje esperado (clave `cargo_ejecutivo`): *"El cargo no corresponde a la entidad seleccionada."*

### Composición de partes por tipo/categoría

Sincronizar partes de un Convenio con una composición inválida para su tipo/categoría (p. ej. un
Marco región sin la parte `GOBIERNO_REGIONAL`):

- Estado esperado: `400` con mensaje de composición inválida (comportamiento sin cambios respecto
  a la versión previa al rename).

### Generación de PDF usa `unidad_organica`

```
POST http://localhost:8000/api/v1/conventions/<id_convenio>/generar-proyecto/
Authorization: Bearer <access>
```

- Estado esperado: `200`/`201` (o el estado normal de generación) sin `AttributeError` referido a
  `organo_directorio`. El PDF debe armar el contexto de la parte y del órgano desde
  `parte.unidad_organica` / `convenio.unidad_organica.organo`.

---

## Rol/permiso requerido por endpoint

| Endpoint | Lectura | Escritura |
|---|---|---|
| `/api/v1/organic-units/` | Autenticado | `Administrador RENADS` (con auditoría) |
| `/api/v1/executive-positions/` | Autenticado | `Administrador RENADS` |
| `/api/v1/conventions/` (incl. `unidad_organica`) | Según alcance del usuario | Según flujo del convenio + `IsModuleEnabled` |
| `/api/v1/conventions/{id}/parties` | Autenticado | Según flujo del convenio |
| `/api/v1/conventions/{id}/generar-proyecto` | — | Según flujo + `IsModuleEnabled` |

---

## Nota de contrato para el frontend (ruptura limpia)

Este refactor **rompe el contrato de API** sin alias temporales:

- `GET /api/v1/organ-directories/` → **404**. Usar `GET /api/v1/organic-units/`.
- Campos de lectura renombrados en convenios/partes/evaluación técnica:
  `organo_directorio` → `unidad_organica`, `organo_directorio_nombre` → `unidad_organica_nombre`,
  `tipo_organo_directorio` → `tipo_unidad_organica`, `organo_directorio_detalle` →
  `unidad_organica_detalle`.
- Filtro de convenios: `?organo_directorio=` → `?unidad_organica=`.
- Serializer de cargos ejecutivos: `organo_directivo` → `unidad_organica` (incluye filtros
  `unidad_organica` y `unidad_organica__isnull`).

## Bug latente conocido (fuera de alcance, preservado)

`load_universidades.py:98` conserva `OrganicUnit.objects.filter(categoria="UNIVERSIDAD")`, donde
`categoria` es un `@property` (no columna): ese `.filter(categoria=...)` lanzaría `FieldError` en
ejecución (bug preexistente). Se dejó **idéntico** por decisión del usuario; no probar como fallo
del refactor.
