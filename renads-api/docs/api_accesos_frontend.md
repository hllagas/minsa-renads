# API de accesos y permisos — Guía para el frontend

Cómo el frontend debe **validar el perfil y los accesos del usuario antes de cualquier
funcionalidad** del módulo Internados (estudiantes, internos, tutores) y cómo resolver el
**ámbito por universidad** (preseleccionar cuando hay una sola, o dejar elegir entre las
permitidas cuando hay varias).

> **Principio.** El backend **siempre** aplica el alcance institucional del lado del servidor
> (no confíes solo en el front). Esta guía describe cómo el front debe **reflejar** ese alcance
> para dar buena UX y evitar 403 innecesarios. La fuente de verdad del acceso del usuario es
> `GET /api/v1/auth/me/`.

---

## 1. Identidad y accesos del usuario — `GET /api/v1/auth/me/`

Al iniciar sesión (y al cargar la app), consulta el perfil del usuario. Requiere
`Authorization: Bearer <access>`.

```bash
curl https://api.renads.minsa.gob.pe/api/v1/auth/me/ -H "Authorization: Bearer $TOKEN"
```

Respuesta:

```json
{
  "id": 12,
  "username": "40123456",
  "email": "docente@unmsm.edu.pe",
  "nombre": "María Pérez",
  "es_superusuario": false,
  "debe_cambiar_password": false,
  "grupos": ["Universidad"],
  "perfiles": [
    { "tipo_entidad": "university", "id_objeto": 3, "entidad": "UNMSM", "rol": "Universidad" },
    { "tipo_entidad": "university", "id_objeto": 7, "entidad": "UPCH", "rol": "Universidad" }
  ],
  "modulos_habilitados": [
    { "app_label": "internados", "model": "internship", "content_type_id": 42 }
  ],
  "modulos_bloqueados": [
    { "app_label": "convenios", "model": "convention", "content_type_id": 31 }
  ]
}
```

- **`grupos`** = roles del usuario (p. ej. `Universidad`, `Administrador RENADS`, `Interno`, `Autoridad de convenio`).
- **`perfiles`** = accesos institucionales: cada uno es una entidad (`tipo_entidad` + `id_objeto` + `entidad` legible) con su `rol`.
  - `tipo_entidad` usa el nombre de modelo en minúscula: `university`, `ipress`, `student`, etc.
- **`es_superusuario`** y el rol **`Administrador RENADS`** están **exentos** del alcance: ven/operan sobre todo.
- **`debe_cambiar_password: true`** ⇒ el interno tiene clave temporal; el front debe forzar el cambio
  antes de dejar operar (ver `docs/api_almacenamiento_frontend.md`).
- **`modulos_habilitados`** / **`modulos_bloqueados`** = estado **temporal** de los módulos gobernados
  por el **Calendario administrativo** (ver §8). Cada item es `{ app_label, model, content_type_id }`.
  Un módulo aparece en `modulos_habilitados` si tiene una ventana de calendario vigente, o en
  `modulos_bloqueados` si está gobernado pero fuera de ventana. Solo aparecen los módulos **gobernados**
  (con `controla_acceso=True`); los no gobernados no figuran en ninguna lista (escritura libre).
  > **Ojo:** estos campos reflejan el estado del módulo, **no** la exención del admin. Para
  > `es_superusuario`/`Administrador RENADS` un módulo fuera de ventana igual aparece en
  > `modulos_bloqueados`, aunque el backend **no** les bloquee la escritura.

### Derivar las universidades accesibles (front)

```js
const me = await fetch("/api/v1/auth/me/", { headers: { Authorization: `Bearer ${access}` } })
  .then((r) => r.json());

const esGlobal = me.es_superusuario || me.grupos.includes("Administrador RENADS");

// Universidades a las que el usuario tiene acceso (si no es global):
const universidades = me.perfiles
  .filter((p) => p.tipo_entidad === "university")
  .map((p) => ({ id: p.id_objeto, nombre: p.entidad }));

// (Análogo para sedes: p.tipo_entidad === "ipress".)
```

---

## 2. Regla de UI para el selector de universidad

Al entrar a cualquier opción del módulo Internados que dependa de una universidad
(estudiantes, internos, registro de tutores, filtros), resuelve el selector así:

| Caso | Comportamiento en el front |
|------|----------------------------|
| Usuario **global** (`es_superusuario` o `Administrador RENADS`) | Cargar el catálogo completo: `GET /api/v1/universities/`. Puede elegir cualquiera. |
| Acceso a **una** universidad | **Preseleccionar por defecto** esa universidad y **bloquear** el selector (o mostrarla como fija). No pedir que elija. |
| Acceso a **varias** universidades | Mostrar **solo** las universidades de `perfiles` (no el catálogo completo) y dejar elegir. |
| **Sin** universidades y no global | No hay ámbito → no mostrar el listado (el backend devolvería vacío / 403 en escritura). |

```js
function resolverUniversidadInicial(me, universidades) {
  if (me.es_superusuario || me.grupos.includes("Administrador RENADS")) {
    return { modo: "catalogo" };                 // cargar /universities/
  }
  if (universidades.length === 1) {
    return { modo: "fija", universidad: universidades[0] };   // preseleccionar + bloquear
  }
  if (universidades.length > 1) {
    return { modo: "elegir", opciones: universidades };       // dropdown con las permitidas
  }
  return { modo: "sin-acceso" };
}
```

---

## 3. Contrato de alcance por recurso (lo que impone el backend)

El backend **filtra en lectura** y **valida en escritura**. El front debe alinear su UI a esto.

| Recurso | Lectura (`GET` list/detail) | Escritura (`POST`/`PUT`/`PATCH`/`DELETE`) |
|---------|------------------------------|-------------------------------------------|
| **Estudiantes** `/api/v1/students/` | Solo estudiantes de **tus universidades**. El rol `Interno` ve **solo su propio** estudiante (lectura). Global ve todos. | Rol `Universidad`/`Administrador RENADS`. Al crear, la `universidad` enviada debe estar en tu ámbito → si no, **403**. |
| **Internos** `/api/v1/interns/` | Internos de **tus universidades o sedes (IPRESS)**. El rol `Interno` ve **solo su propio** internado. Global ve todos. | Crear: rol `Universidad` + la universidad del estudiante en tu ámbito (**403** si no). Acciones de flujo con su rol (p. ej. `revisar-declaraciones`). Adjunto de DJ (`annex-upload`/`annex-checklist`, actor `INTERNO`) **sobre el internado**: rol `Universidad`/`Administrador RENADS` o el propio `Interno`. |
| **Tutores** `/api/v1/tutors/` | Autenticados (los tutores son compartidos, no acotados por universidad). | Rol `Universidad`/`Administrador RENADS`. Al asignar `universidades` (RN-24, 1 a 2) usa **solo** las universidades permitidas del usuario. |
| **Rotaciones** `/api/v1/rotations/` | Rotaciones de tus internos (según tu ámbito). | Acciones con su rol (`autorizar`, `iniciar`, `cambiar-estado`). |

**Filtros útiles (query params):**
- `GET /api/v1/students/?universidad=<id>` — acota a una universidad (dentro de tu ámbito).
- `GET /api/v1/students/?carrera_profesional=<id>` — acota por carrera profesional.
- `GET /api/v1/tutors/?universidades=<id>` — tutores de una universidad.
- `GET /api/v1/interns/?...` — filtros de internos (convenio, ipress, tutor, estado, ámbito, fechas).

> **Preselección con filtro:** cuando el selector quede **fijo** en una universidad (caso "una sola"),
> el front debe enviar siempre `?universidad=<id>` en los listados y fijar ese `universidad` en los
> formularios de alta, para que coincida con lo que el backend ya está filtrando.

---

## 4. Carreras profesionales y otros catálogos

- **Carreras** `GET /api/v1/professional-careers/`: catálogo **global** (no está acotado por
  universidad en el modelo de datos). Úsalo para poblar el selector de carrera del estudiante;
  filtra los estudiantes por `?carrera_profesional=<id>` si necesitas segmentar.
- **Universidades** `GET /api/v1/universities/` e **IPRESS** `GET /api/v1/ipress/`: catálogos de
  entidades. Para usuarios no globales, **no** los uses como fuente del selector de ámbito: usa
  `perfiles` de `/auth/me/` (solo lo permitido). Sí puedes usarlos para mostrar nombres/detalle.
- **Clasificación y jerarquía de IPRESS** (CRUD, escritura solo `Administrador RENADS`; lectura para
  autenticados). Úsalos para poblar los selectores del formulario de IPRESS:
  - **Categoría** `GET /api/v1/categories/` y **Tipo de clasificación** `GET /api/v1/classification-types/`.
  - **Ámbito geográfico sanitario** `GET /api/v1/health-geographic-scopes/` (CRUD, escritura solo
    `Administrador RENADS`; antes solo lectura). Raíz de la jerarquía `ámbito → red → microred`.
  - **Redes** `GET /api/v1/networks/` (filtrable `?ambito_geografico_sanitario=<id>`) y **Microredes**
    `GET /api/v1/micro-networks/` (filtrable `?red=<id>`). Jerarquía `ámbito → red → microred`; encadena
    los selectores por esos filtros. La IPRESS referencia la `microred` (`GET /api/v1/ipress/?microred=<id>`).
- **Otros catálogos** del módulo (estados, tipos de documento, parentesco, periodos académicos,
  documentos anexos) son de solo lectura para autenticados.

---

## 4 bis. Campos clínicos — registro (CONAPRES) y asignación (Órgano Regional)

Los campos clínicos que habilitan el registro de internos se modelan en **dos recursos
encadenados**. El interno se asigna a una **asignación por universidad**
(`interno.campo_clinico_id` → `clinical-field-allocations`), no al registro global.

| Recurso | Tabla | Escritura | Lectura | Filtros (query params) |
|---------|-------|-----------|---------|-------------------------|
| **Registro** `/api/v1/clinical-field-registrations/` | `campo_clinico_ipress` | Rol **CONAPRES** (superusuario exento) | Autenticados | `convenio`, `ipress`, `carrera_profesional`, `especialidad` |
| **Asignación** `/api/v1/clinical-field-allocations/` | `campo_clinico_ipress_universidad` | Grupo **Gobierno Regional** (superusuario exento) | Autenticados | `campo_clinico_ipress`, `convenio`, `ipress`, `carrera_profesional`, `universidad` |

> **Reemplaza** la antigua action anidada `POST /api/v1/conventions/{id}/campos-clinicos/` (retirada).
> Ambos son CRUD standalone bajo `/api/v1/`.

### Encadenamiento registro → asignación (front)

1. **CONAPRES** crea el **registro** por sede docente (`ipress`) + carrera: define
   `campos_clinicos_registrados` (el total/tope).
2. El **Órgano Regional** crea **asignaciones** por universidad contra ese registro
   (`campo_clinico_ipress` = id del registro), enviando `universidad`, `convenio` (Específico
   vigente cuya universidad debe coincidir), `fecha_inicio`, `fecha_fin` y
   `campos_clinicos_autorizados`. `ipress` y `carrera_profesional` deben coincidir con el registro padre.
3. Al registrar un **interno**, el selector de campo clínico se puebla con las **asignaciones**
   (`clinical-field-allocations`) de la universidad y sede correspondientes.

### Disponibilidad (lo que valida el backend)

- El **registro** expone `disponibilidad = campos_clinicos_registrados − campos_clinicos_asignados`
  (computed) y `campos_clinicos_asignados` (acumulador Σ de las asignaciones; **solo lectura**).
- Al crear/editar una **asignación**, el backend exige
  `campos_clinicos_autorizados ≤ campos_clinicos_registrados − Σ autorizados de las demás asignaciones
  del mismo registro`; si se excede, responde **400**. Tras cada create/update/delete el service
  **recalcula** `campos_clinicos_asignados` del registro padre.
- Mostrar `disponibilidad` del registro seleccionado como tope del input de cupos en el formulario
  de asignación, para anticipar el 400.
- Escritura sin el rol correspondiente ⇒ **403** ("La escritura requiere el rol CONAPRES." /
  "La escritura requiere el rol Gobierno Regional.").

---

## 5. Flujo recomendado al entrar al módulo Internados

1. `GET /api/v1/auth/me/` → guarda `grupos`, `perfiles`, `es_superusuario`, `debe_cambiar_password`.
2. Si `debe_cambiar_password` → forzar cambio de clave (`POST /api/v1/auth/me/cambiar-password/`) antes de continuar.
3. Deriva `universidades` accesibles (§1) y resuelve el selector (§2).
4. Muestra/oculta acciones de **escritura** según el rol (§3): si el usuario no tiene rol de escritura,
   deshabilita botones de alta/edición (el backend igualmente responderá **403**).
5. En listados, envía el filtro de universidad activo; en formularios de alta, fija/limita la
   universidad (y, para tutores, el multiselect de `universidades`) a lo permitido.

---

## 6. Errores de acceso (mensajes en español)

| Código | Situación | Acción del front |
|--------|-----------|------------------|
| `401` | Token ausente/expirado. | Redirigir a login / refrescar token (`POST /api/v1/auth/token/refresh/`). |
| `403` | Autenticado sin rol o **fuera del ámbito institucional** (p. ej. crear un estudiante de una universidad no permitida). | No es recuperable reintentando: revisar rol/ámbito; ocultar la acción. Mensaje del backend: "La entidad indicada está fuera de tu ámbito institucional." / "La escritura requiere el rol Universidad o Administrador RENADS." |
| `400` | Datos inválidos (p. ej. tutor con 0 o más de 2 universidades — RN-24). | Mostrar el detalle de validación por campo. |

---

## 7. Roles (grupos) relevantes

| Rol (`grupos`) | Puede |
|----------------|-------|
| `Administrador RENADS` | Todo el módulo, **sin** restricción de ámbito. |
| `Universidad` | Registrar/ver estudiantes, internos y tutores **de sus universidades** (1..N por `perfiles`). |
| `Interno` | **Solo lectura** de sus propios datos + adjuntar sus declaraciones juradas (`annex-upload`/`annex-checklist`). |
| `Autoridad de convenio` | Autorizar rotaciones (`rotations/{id}/autorizar`). |
| `CONAPRES` | Registrar el total de campos clínicos por sede/carrera (`clinical-field-registrations`). |
| `Gobierno Regional` | Asignar cupos de campos clínicos por universidad (`clinical-field-allocations`). |

> El backend es la última línea: aunque el front oculte una acción, la API revalida rol y ámbito en
> cada request. La UI solo **anticipa** el resultado para mejor experiencia.

---

## 8. Calendario administrativo — habilitación temporal de módulos

El módulo **Calendario administrativo** gobierna **cuándo** se puede escribir en ciertos módulos.
Una **actividad de calendario** con `controla_acceso=true` define una **ventana de fechas**
(`fecha_inicio`..`fecha_fin`) durante la cual se habilita la escritura de los modelos que referencia
(`content_types`). Fuera de esa ventana, la escritura de esos módulos responde **403**.

- **`fecha_fin` NULL = ventana abierta** (sin cierre): vigente indefinidamente desde `fecha_inicio`.
- **OR entre ventanas:** basta **una** actividad controladora con ventana vigente para habilitar el módulo.
- **Módulo no gobernado** (ningún calendario lo referencia) ⇒ escritura siempre libre (*pass-through*).
- **Exentos del bloqueo:** `es_superusuario` y `Administrador RENADS` (pero ver la nota de §1: igual
  figuran en `modulos_bloqueados` si el módulo está fuera de ventana).

### 8.1. Cómo el front gatea nav y acciones

La fuente de verdad para el front son `modulos_habilitados` / `modulos_bloqueados` de
`GET /api/v1/auth/me/` (§1). Con ellas:

- **Navegación:** si un módulo (p. ej. `convenios/convention`) está en `modulos_bloqueados` y el usuario
  **no** es global, atenúa/oculta las acciones de **alta/edición** de ese módulo y muestra el motivo
  ("fuera de la ventana de registro"). La **lectura** siempre está permitida (no la bloquees).
- **Botones de escritura:** habilítalos solo si el módulo está en `modulos_habilitados` **o** no aparece
  en ninguna lista (no gobernado) **o** el usuario es global. Aun así, el backend revalida.
- **Manejo del 403 de calendario:** si un `POST/PUT/PATCH/DELETE` a un módulo gobernado devuelve **403**
  con `code = "MODULO_FUERA_DE_VENTANA"`, muestra el mensaje del backend ("El módulo está fuera de su
  ventana de registro.") y refresca `/auth/me/` para re-sincronizar el estado.

```js
const me = await fetch("/api/v1/auth/me/", { headers: { Authorization: `Bearer ${access}` } })
  .then((r) => r.json());

const esGlobal = me.es_superusuario || me.grupos.includes("Administrador RENADS");
const bloqueados = new Set(me.modulos_bloqueados.map((m) => `${m.app_label}.${m.model}`));

// ¿Puede el usuario escribir en un módulo dado ahora mismo?
function puedeEscribirModulo(appLabel, model) {
  if (esGlobal) return true;                 // el admin no queda bloqueado por la ventana
  return !bloqueados.has(`${appLabel}.${model}`); // habilitado o no gobernado
}
// p. ej. puedeEscribirModulo("internados", "internship")
```

### 8.2. Endpoint `GET /api/v1/content-types/` (solo lectura, autenticados)

Lista los `ContentType` de Django con `{ id, app_label, model, verbose_name }`. Úsalo para:
- poblar el selector `content_types[]` del CRUD de `calendar-activities`;
- resolver el nombre legible (`verbose_name`) de los ítems de `modulos_habilitados`/`modulos_bloqueados`
  (empatando por `content_type_id` o por `app_label`+`model`).

### 8.3. CRUD `/api/v1/calendar-activities/`

| Método | Escritura | Lectura |
|--------|-----------|---------|
| `GET` (list/detail) | — | Autenticados |
| `POST` / `PUT` / `PATCH` / `DELETE` | Rol `Administrador RENADS` (con auditoría) | — |

- **Lectura** expone, además de los campos base (`nombre`, `detalle`, `responsables`, `numero_orden`,
  `fecha_inicio`, `fecha_fin`, `controla_acceso`, `activo` y auditoría): `content_types_detalle`
  (`[{ id, app_label, model, verbose_name }]` de los módulos). `responsables` es un campo de **texto
  libre** (string).
- **Escritura** recibe `responsables` (texto libre) y `content_types` (lista de ids de
  ContentType). Validación: si `fecha_fin` no es nula, debe ser `>= fecha_inicio`.
- **Filtros (query params):** `controla_acceso` (bool), `activo` (bool), `content_types` (id) y rango de
  fechas.

### 8.4. Errores propios del calendario

| Código | Situación | Acción del front |
|--------|-----------|------------------|
| `403` (`code = "MODULO_FUERA_DE_VENTANA"`) | Escritura a un módulo gobernado fuera de su ventana de registro. | Mostrar el mensaje del backend; ocultar/atenuar la acción; refrescar `/auth/me/`. |
