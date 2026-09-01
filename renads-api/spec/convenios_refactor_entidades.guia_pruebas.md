# Guía de pruebas manuales — Refactor de entidades del módulo Convenios

Objetivo: que un QA verifique end-to-end el refactor de entidades sin leer el código. Cubre la retirada de `organ-types` (404), el discriminador `categoria` en `organ-directories`, el reapuntado de `executing-units`/`universities` a `organo_directorio`, los nuevos campos de `regional-governments` (ubigeo/sigla) y `faculties` (logo/ubigeo), los nombres por género de `executive-positions`, la RN-1 (Marco/Específico DIRIS) y el comando `load_universidades`.

Fecha: 2026-08-31.

---

## 1. Prerrequisitos

1. **Levantar el servidor** (lo corre el usuario, no el QA por API):
   ```
   .venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. **URL base:** `http://localhost:8000/api/v1/`
3. **Swagger interactivo (alternativa):** `http://localhost:8000/api/v1/docs/`
4. **Obtener token JWT** (usuario con rol `Administrador RENADS` para las pruebas de escritura de catálogos):
   ```
   POST http://localhost:8000/api/v1/auth/token/
   Content-Type: application/json

   { "username": "admin", "password": "<contraseña>" }
   ```
   Respuesta `200`: `{ "access": "<jwt>", "refresh": "<jwt>" }`.
   En todas las llamadas siguientes añadir el header:
   ```
   Authorization: Bearer <access>
   ```

---

## 2. Datos previos necesarios

- **`organo`** (categorías canónicas) y **`organo_directorio`** deben estar seedeados/migrados. Tras la migración `0029`, cada antiguo `tipo_organo` produjo una fila en `organo_directorio` con su `categoria`.
- **`ubigeo`** cargado (`python manage.py load_ubigeo`) para probar `regional-governments`/`faculties`.
- **`gobierno_regional`** cargado (`python manage.py load_gobiernos_regionales`).
- Existir al menos una **universidad** con `tipo_entidad` apuntando a un `organo_directorio` de categoría `UNIVERSIDAD` y una **facultad** de esa universidad.
- Rol/permiso: **la escritura de todos los catálogos de este módulo requiere el grupo `Administrador RENADS`** (o superusuario). La lectura (`GET`) solo requiere estar autenticado.

Verificar rápidamente que la migración corrió y el modelo está limpio (lo corre el usuario, no runserver):
```
python manage.py makemigrations --check --dry-run   # → No changes detected
python manage.py check                              # → 0 issues
```

---

## 3. Escenarios

### 3.1. `organ-types` retirado → 404

El endpoint fue eliminado por el refactor. Debe devolver 404.

```
GET http://localhost:8000/api/v1/organ-types/
Authorization: Bearer <access>
```
**Esperado:** `404 Not Found`.

Verificar también que su reemplazo funcional (`organ-directories`) sí existe:
```
GET http://localhost:8000/api/v1/organ-directories/
```
**Esperado:** `200` con lista paginada; cada item incluye `categoria` (una de `ORGANO_MINSA`, `UNIVERSIDAD`, `GOBIERNO_REGIONAL`, `MINSA_DIRIS`, `UNIDAD_EJECUTORA`), `nombre`, `siglas`, `gobierno_regional`, `gobierno_regional_detalle`, `activo`.

### 3.2. Filtros de `organ-directories` por categoría

```
GET http://localhost:8000/api/v1/organ-directories/?categoria=UNIDAD_EJECUTORA
GET http://localhost:8000/api/v1/organ-directories/?categoria=UNIVERSIDAD
GET http://localhost:8000/api/v1/organ-directories/?categoria=GOBIERNO_REGIONAL
GET http://localhost:8000/api/v1/organ-directories/?categoria=MINSA_DIRIS
```
**Esperado:** `200`; todos los resultados de cada llamada tienen exactamente esa `categoria`. Filtros adicionales disponibles: `gobierno_regional`, `activo`; búsqueda `?search=` sobre `nombre`/`siglas`.

### 3.3. `executing-units` reapuntadas a `organo_directorio`

El campo `tipo_organo` de una unidad ejecutora ahora es FK a `organo_directorio` (categoría `UNIDAD_EJECUTORA`), no a la tabla retirada `tipo_organo`.

Listado + detalle:
```
GET http://localhost:8000/api/v1/executing-units/
```
**Esperado:** `200`; cada item expone `tipo_organo` (id de `organo_directorio`), `tipo_organo_detalle` (nombre), `gobierno_regional` + `gobierno_regional_detalle`, `ubigeo` + `ubigeo_detalle`, `referencia_logo`.

Filtrar por el nuevo id de directorio (tomar un id de 3.2 con `categoria=UNIDAD_EJECUTORA`):
```
GET http://localhost:8000/api/v1/executing-units/?tipo_organo=<id_directorio_unidad_ejecutora>
```
**Esperado:** `200`; solo unidades con ese `tipo_organo`.

Crear una unidad ejecutora (rol `Administrador RENADS`):
```
POST http://localhost:8000/api/v1/executing-units/
Authorization: Bearer <access>
Content-Type: application/json

{
  "codigo": "UE-QA-001",
  "nombre": "Unidad Ejecutora QA",
  "tipo_organo": <id_directorio_unidad_ejecutora>,
  "gobierno_regional": <id_gobierno_regional>,
  "direccion": "Av. Salud 123",
  "activo": true
}
```
**Esperado:** `201`; el `id` devuelto alimenta escenarios de convenios. Enviar en `tipo_organo` un id de directorio con `categoria != UNIDAD_EJECUTORA` debe fallar con `400` (`limit_choices_to`).

### 3.4. `universities` reapuntadas a `organo_directorio`

```
GET http://localhost:8000/api/v1/universities/
```
**Esperado:** `200`; `tipo_entidad` es id de `organo_directorio` (categoría `UNIVERSIDAD`) con `tipo_entidad_detalle`; también `tipo_gestion(_detalle)`, `tipo_autorizacion(_detalle)`, `referencia_logo`, `numero_ruc`, `siglas`.

Filtrar por el nuevo id de directorio:
```
GET http://localhost:8000/api/v1/universities/?tipo_entidad=<id_directorio_universidad>
```
**Esperado:** `200`; solo universidades con ese `tipo_entidad`. Otros filtros: `tipo_gestion`, `tipo_autorizacion`, `activo`; búsqueda `?search=` sobre `nombre`/`siglas`/`numero_ruc`.

### 3.5. `regional-governments` — ubigeo + sigla

```
GET http://localhost:8000/api/v1/regional-governments/
```
**Esperado:** `200`; cada item expone `sigla`, `ubigeo` + `ubigeo_detalle`, además de los campos de contacto ya migrados.

Actualizar sigla y ubigeo (rol `Administrador RENADS`):
```
PATCH http://localhost:8000/api/v1/regional-governments/<id>/
Authorization: Bearer <access>
Content-Type: application/json

{ "sigla": "GORE-LIM", "ubigeo": <id_ubigeo> }
```
**Esperado:** `200`; respuesta refleja `sigla` y `ubigeo_detalle`. Filtros: `region`, `ubigeo`, `activo`.

### 3.6. `faculties` — logo + ubigeo

```
GET http://localhost:8000/api/v1/faculties/
```
**Esperado:** `200`; cada facultad expone `referencia_logo` y `ubigeo` (+ detalle si aplica), además de `universidad`/`universidad_detalle`.

Subir logo + ubigeo (multipart, rol `Administrador RENADS`):
```
PATCH http://localhost:8000/api/v1/faculties/<id>/
Authorization: Bearer <access>
Content-Type: multipart/form-data

referencia_logo=@logo.png
ubigeo=<id_ubigeo>
```
**Esperado:** `200`; `referencia_logo` con la URL del medio almacenado y `ubigeo` seteado.

### 3.7. `executive-positions` — nombres por género

El campo único `nombre` fue reemplazado por `nombre_masculino` (requerido) + `nombre_femenino` (opcional); la unicidad es por `(organo, nombre_masculino)` y ya no existe `codigo`.

```
GET http://localhost:8000/api/v1/executive-positions/
```
**Esperado:** `200`; cada item expone `nombre_masculino`, `nombre_femenino`, `organo` + `organo_detalle`, `activo`. **No** aparece `codigo`.

Crear (rol `Administrador RENADS`):
```
POST http://localhost:8000/api/v1/executive-positions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "organo": <id_organo>,
  "nombre_masculino": "Director",
  "nombre_femenino": "Directora",
  "activo": true
}
```
**Esperado:** `201`. Búsqueda `?search=Director` matchea ambos géneros; filtro `?organo=<id>`.

**Caso que debe fallar (unicidad):** repetir el POST anterior con el mismo `organo` y `nombre_masculino`.
**Esperado:** `400` por violación de `unique_together (organo, nombre_masculino)`.

### 3.8. RN-1 — Convenio Marco vs. Específico DIRIS

**RN-1:** un Convenio Específico requiere Convenio Marco vigente, **excepto las DIRIS** (categoría `MINSA_DIRIS`), que no lo requieren.

Caso A — Específico **sin** Marco para un órgano NO-DIRIS (GERESA/DIRESA) → debe fallar:
```
POST http://localhost:8000/api/v1/conventions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo": "ESPECIFICO",
  "convenio_marco": null,
  "universidad": <id_universidad>,
  "organo_directorio": <id_directorio_gobierno_regional_no_diris>,
  "unidad_ejecutora": <id_unidad_ejecutora>,
  "facultad": <id_facultad>,
  "titulo": "Convenio Específico QA sin marco"
}
```
**Esperado:** `400`, mensaje del tipo "Convenio Específico requiere un Convenio Marco vigente".

Caso B — Específico **sin** Marco para una **DIRIS** (categoría `MINSA_DIRIS`) → debe permitirse:
```
POST http://localhost:8000/api/v1/conventions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo": "ESPECIFICO",
  "convenio_marco": null,
  "universidad": <id_universidad>,
  "organo_directorio": <id_directorio_MINSA_DIRIS>,
  "unidad_ejecutora": <id_unidad_ejecutora>,
  "facultad": <id_facultad_de_esa_universidad>,
  "titulo": "Convenio Específico DIRIS sin marco"
}
```
**Esperado:** `201`. (La categoría del `organo_directorio` = `MINSA_DIRIS` es lo que exime del Marco.)

Caso C — coherencia de partes por tipo: un Específico **exige** `unidad_ejecutora` y `facultad`; omitir cualquiera →
**Esperado:** `400`. Un Marco no debe llevar ninguno de los dos.

### 3.9. Comando `load_universidades` (carga masiva)

Lo ejecuta el usuario en terminal (no por API). Verifica que la carga masiva usa los **ids del directorio** (`organo_directorio`, categoría `UNIVERSIDAD`) en la columna `tipo_entidad_id`, no los ids de la retirada `tipo_organo`.

```
python manage.py load_universidades --file Universidades.xlsx --dry-run
python manage.py load_universidades --file Universidades.xlsx
```
Estructura del Excel (fila 1 = encabezados): `nombre, siglas, codigo_inei, fecha_constitucion, fecha_autorizacion, numero_resolucion, direccion_legal, telefono, correo_institucional, referencia_logo, activo, tipo_autorizacion_id, tipo_gestion, ubigeo_id, tipo_entidad_id`.

Puntos a verificar:
- `tipo_entidad_id` = id de `organo_directorio` categoría `UNIVERSIDAD` (obtener de 3.2). Un id inexistente/erróneo debe reportar error de validación en el `--dry-run`.
- `ubigeo_id` = **código INEI** del distrito (no el PK); si no existe, la universidad se carga con `ubigeo` nulo.
- Idempotente por `nombre` (`update_or_create`): re-ejecutar no duplica.
- Tras cargar, `GET /api/v1/universities/?tipo_entidad=<id_directorio_universidad>` lista las universidades importadas.

---

## 4. Resumen de rol/permiso por endpoint

| Endpoint | Lectura | Escritura |
|----------|---------|-----------|
| `organ-directories`, `executing-units`, `universities`, `regional-governments`, `faculties`, `executive-positions` | autenticado | `Administrador RENADS` / superusuario |
| `conventions` | autenticado (con alcance por perfil) | según flujo del módulo; ver `spec/convenios.md` |
| `organ-types` | — (404, retirado) | — |
| `load_universidades` | — (comando de gestión) | ejecutado por el usuario en terminal |
