# Guía de pruebas manuales — Refactor `gobierno_regional` a `convenio`

> Módulo: **Gestionar Convenios** (`apps/convenios`)
> Valida el traslado del FK `gobierno_regional` de `organo_directorio` a `convenio`.
> Estado de la validación: **OK** (sin errores altos/medios). Ver `convenios_organo_directorio_gore.validacion.md`.

Todas las llamadas usan la URL base `http://localhost:8000/api/v1/`. El servidor lo levanta el usuario con `python manage.py runserver`.

---

## 1. Prerrequisitos

1. **Servidor arriba:** `python manage.py runserver` (lo corre el usuario).
2. **Migrar** (lo corre el usuario): `python manage.py migrate` — aplica `0041_convention_gobierno_regional_drop_organdirectory_gore`.
3. **Obtener token JWT:**

```http
POST /api/v1/auth/token/
Content-Type: application/json

{ "username": "<usuario>", "password": "<password>" }
```

Respuesta: `{ "access": "...", "refresh": "..." }`. En las siguientes llamadas enviar el header:

```
Authorization: Bearer <access>
```

4. **Alternativa interactiva:** Swagger en `/api/v1/docs/`.
5. **Rol requerido:**
   - CRUD de `organ-directories` y creación/edición de convenios (write): grupo **`Administrador RENADS`** (o superusuario).
   - Lectura (`GET`): cualquier usuario autenticado.

---

## 2. Datos previos necesarios

Deben existir (seedeados o creados vía API por `Administrador RENADS`):

- Al menos un `regional-governments` (tabla `gobierno_regional`) con `direccion` y `sigla` — anotar su `id` como `{GORE_ID}`.
- Órganos del directorio (`organ-directories`) de categoría/`organo` **GOBIERNO_REGIONAL** (para Marco regional) y **MINSA_DIRIS** (para Marco Lima) — anotar `id` como `{ORGANO_GORE_ID}` y `{ORGANO_DIRIS_ID}`.
- Una `universities` — anotar `id` como `{UNIV_ID}`.
- Un `convention-types` con `codigo = MARCO` y otro con `codigo = ESPECIFICO`.
- El `content_type` del solicitante (p. ej. `universidad`) para `solicitante_tipo_contenido` / `solicitante_id_objeto`.

---

## 3. Verificación del catálogo `organ-directories` (ya sin GORE)

### 3.1 El endpoint ya NO acepta el filtro `gobierno_regional`

```http
GET /api/v1/organ-directories/?gobierno_regional=1
Authorization: Bearer <access>
```

**Esperado:** `200` devolviendo la lista **sin** aplicar ese filtro (DRF ignora un parámetro no declarado en `filterset_fields`). El listado **no** debe romper. Filtros válidos ahora: `organo`, `activo`.

### 3.2 La lectura ya NO expone `gobierno_regional` ni `gobierno_regional_detalle`

```http
GET /api/v1/organ-directories/{ORGANO_GORE_ID}/
Authorization: Bearer <access>
```

**Esperado:** `200`. El objeto **no** contiene las claves `gobierno_regional` ni `gobierno_regional_detalle`.

### 3.3 Unicidad por `(organo, nombre)` — debe fallar con 400 legible

Crear un órgano del directorio (rol `Administrador RENADS`):

```http
POST /api/v1/organ-directories/
Authorization: Bearer <access>
Content-Type: application/json

{ "organo": {ORGANO_GORE_ID_organo}, "nombre": "GERESA Piura", "siglas": "GRP", "activo": true }
```

**Esperado:** `201`. Repetir el **mismo** POST con idéntico `(organo, nombre)`:

**Esperado:** `400` con mensaje en español sobre `nombre`:
`"Ya existe un órgano del directorio con este nombre para el mismo órgano."`
(No debe devolver `500`/IntegrityError.)

---

## 4. Convenio Marco regional — `gobierno_regional` obligatorio (RN-GORE-1/2)

Rol requerido: `Administrador RENADS`.

### 4.1 Marco regional CON `gobierno_regional` — éxito

```http
POST /api/v1/conventions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_convenio": {TIPO_MARCO_ID},
  "titulo": "Convenio Marco GERESA Piura - UNP",
  "solicitante_tipo_contenido": {CT_UNIVERSIDAD_ID},
  "solicitante_id_objeto": {UNIV_ID},
  "organo_directorio": {ORGANO_GORE_ID},
  "gobierno_regional": {GORE_ID},
  "universidad": {UNIV_ID},
  "fecha_solicitud": "2026-09-07"
}
```

**Esperado:** `201`. Anotar el `id` como `{CONV_MARCO_ID}`.

### 4.2 Marco regional SIN `gobierno_regional` — debe fallar (RN-GORE-2)

Mismo payload que 4.1 pero **omitiendo** `gobierno_regional`:

**Esperado:** `400` con:
`{ "gobierno_regional": "Requerido para un Convenio Marco regional." }`

### 4.3 Lectura del convenio expone el GORE

```http
GET /api/v1/conventions/{CONV_MARCO_ID}/
Authorization: Bearer <access>
```

**Esperado:** `200` con:
- `gobierno_regional`: `{GORE_ID}`.
- `gobierno_regional_detalle`: `{ "id": {GORE_ID}, "nombre": "...", "sigla": "..." }`.

---

## 5. Convenio Marco Lima (DIRIS) — `gobierno_regional` debe ser nulo

### 5.1 Marco Lima CON `gobierno_regional` — debe fallar

```http
POST /api/v1/conventions/
Authorization: Bearer <access>
Content-Type: application/json

{
  "tipo_convenio": {TIPO_MARCO_ID},
  "titulo": "Convenio Marco DIRIS Lima",
  "solicitante_tipo_contenido": {CT_UNIVERSIDAD_ID},
  "solicitante_id_objeto": {UNIV_ID},
  "organo_directorio": {ORGANO_DIRIS_ID},
  "gobierno_regional": {GORE_ID},
  "universidad": {UNIV_ID},
  "fecha_solicitud": "2026-09-07"
}
```

**Esperado:** `400` con:
`{ "gobierno_regional": "Un Convenio Marco de Lima (DIRIS) no lleva gobierno regional." }`

### 5.2 Marco Lima SIN `gobierno_regional` — éxito

Mismo payload que 5.1 pero **omitiendo** `gobierno_regional`:

**Esperado:** `201`. En la lectura, `gobierno_regional` = `null` y `gobierno_regional_detalle` = `null`.

---

## 6. Convenio Específico — `gobierno_regional` debe ser nulo

### 6.1 Específico CON `gobierno_regional` — debe fallar

Crear un Específico (requiere Marco vigente según RN-3, o DIRIS) enviando además `gobierno_regional`:

**Esperado:** `400` con:
`{ "gobierno_regional": "Un Convenio Específico no lleva gobierno regional." }`

### 6.2 Específico SIN `gobierno_regional` — éxito

Sin la clave `gobierno_regional` → el flujo del Específico procede normal (`201` si cumple las demás RN).

---

## 7. Edición (PATCH) — revalidación de la regla (RN-GORE-1/2)

### 7.1 Quitar el GORE de un Marco regional — debe fallar

```http
PATCH /api/v1/conventions/{CONV_MARCO_ID}/
Authorization: Bearer <access>
Content-Type: application/json

{ "gobierno_regional": null }
```

**Esperado:** `400` (`"Requerido para un Convenio Marco regional."`). La revalidación corre contra el estado final del objeto.

### 7.2 Cambiar el GORE por otro válido — éxito

```http
PATCH /api/v1/conventions/{CONV_MARCO_ID}/
Authorization: Bearer <access>
Content-Type: application/json

{ "gobierno_regional": {OTRO_GORE_ID} }
```

**Esperado:** `200`; la lectura refleja el nuevo `gobierno_regional_detalle`.

---

## 8. Adenda — hereda `gobierno_regional` del origen (RN-GORE-4)

```http
POST /api/v1/conventions/{CONV_MARCO_ID}/adenda
Authorization: Bearer <access>
Content-Type: application/json

{ "fecha_inicio": "2027-01-01" }
```

**Esperado:** `201`. Anotar `id` de la adenda como `{ADENDA_ID}` y verificar:

```http
GET /api/v1/conventions/{ADENDA_ID}/
Authorization: Bearer <access>
```

**Esperado:** `gobierno_regional` de la adenda **igual** al del `CONV_MARCO_ID` origen (heredado).

---

## 9. Regresión — PDF del proyecto (parte GOBIERNO_REGIONAL)

Con un Marco regional que tenga `gobierno_regional` con `direccion`:

```http
POST /api/v1/conventions/{CONV_MARCO_ID}/generar-proyecto
Authorization: Bearer <access>
```

**Esperado:** `200`/`201` con el PDF generado/adjunto. El domicilio de la parte `GOBIERNO_REGIONAL` en el documento debe corresponder a `convenio.gobierno_regional.direccion` (ya no al órgano del directorio). Si el GORE no tuviera dirección, el campo sale vacío pero **no** lanza error.

---

## 10. Verificación de datos migrados (RN-GORE-6)

Tras `migrate`, si en la base existían órganos del directorio con GORE y convenios que los referenciaban, cada uno de esos convenios debe tener ahora `convenio.gobierno_regional` = el GORE que tenía su órgano. (Al momento del refactor: 3 órganos con GORE y 0 convenios que los referenciaran → sin filas a actualizar.)
