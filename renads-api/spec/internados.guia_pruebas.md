# Guía de pruebas manuales — Módulo `internados`

Cómo probar manualmente los endpoints del módulo. Generada por el agente **validator** tras validación exitosa.

## Prerrequisitos

1. Servidor: `python manage.py runserver` (lo corre el usuario). Base: `http://localhost:8000/api/v1/`. Swagger: `/api/v1/docs/`.
2. **Token JWT:** `POST /api/v1/auth/token/` → usar `Authorization: Bearer <access>`.
3. **Roles usados:** `Universidad` (registrar estudiantes/tutores/internados/rotaciones, iniciar rotación), `Autoridad de convenio` (autorizar rotación), `Administrador RENADS` (transiciones de estado). Atajo camino feliz: superusuario.
4. **Datos del módulo 1 ya existentes** (crear con la guía de `convenios` o seed): un **Convenio Específico VIGENTE**, un **campo clínico** asociado, e **IPRESS** del mismo ámbito geográfico sanitario. Catálogos seedeados: `internship-statuses` (12), `rotation-statuses` (8), `identity-document-types` (`DNI`/`CE`/`PASAPORTE`); crear `service-areas` si hace falta.

## Flujo paso a paso

1. **Registrar estudiante** (rol `Universidad`; la universidad debe estar en tu ámbito):
   ```
   POST /api/v1/students/
   { "tipo_documento_identidad": <id DNI>, "numero_documento": "70011223",
     "nombres": "Ana", "apellido_paterno": "López", "universidad": <UNI>,
     "carrera_profesional": <id> }
   → 201  (creado_por se asigna solo)   (guardar id = INTERNO)
   ```
2. **Registrar tutor** (rol `Universidad`):
   ```
   POST /api/v1/tutors/
   { "tipo_documento_identidad": <id DNI>, "numero_documento": "10203040",
     "nombres": "Carlos", "apellido_paterno": "Ríos" }
   → 201   (guardar id = TUTOR)
   ```
3. **Crear internado** (rol `Universidad`):
   ```
   POST /api/v1/interns/
   { "estudiante": INTERNO, "convenio": <ESP vigente>, "campo_clinico": <id>,
     "ipress": <id IP1>, "tutor": TUTOR, "ambito_geografico_sanitario": <id>,
     "fecha_inicio": "2026-04-01", "fecha_fin": "2026-12-01" }
   → 201  estado_codigo="REGISTRADO"   (guardar id = INT)
   ```
4. **Activar internado** (rol `Administrador RENADS`):
   ```
   POST /api/v1/interns/{INT}/cambiar-estado/
   { "estado_codigo": "ACTIVO" }
   → 200  estado_codigo="ACTIVO"
   ```
5. **Solicitar rotación** (rol `Universidad`; ambas sedes del mismo ámbito que el internado):
   ```
   POST /api/v1/interns/{INT}/rotaciones/
   { "ipress_origen": <IP1>, "ipress_destino": <IP2>, "servicio_area": <id>,
     "fecha_inicio": "2026-05-01", "fecha_fin": "2026-06-01" }
   → 200 (lista de rotaciones; la nueva tiene numero_rotacion=1)   (guardar id = ROT)
   ```
6. **Autorizar rotación** (rol `Autoridad de convenio`; el participante debe ser firmante del Convenio Específico):
   ```
   POST /api/v1/rotations/{ROT}/autorizar/
   { "participante_convenio": <id participante firmante>, "resultado": "APROBADO",
     "fecha_autorizacion": "2026-04-20" }
   → 200  estado_codigo="AUTORIZADA"
   ```
7. **Iniciar rotación** (rol `Universidad`):
   ```
   POST /api/v1/rotations/{ROT}/iniciar/
   {}
   → 200  estado_codigo="EN_CURSO"
   ```
8. **Cambiar tutor** (rol `Universidad`, queda en historial — RN-14):
   ```
   POST /api/v1/interns/{INT}/cambiar-tutor/
   { "tutor": <id otro tutor>, "fecha_cambio": "2026-06-15", "motivo": "Rotación de docente" }
   → 200
   ```
9. **Consultar historiales:**
   ```
   GET /api/v1/interns/{INT}/historial/      → estados del internado
   GET /api/v1/rotations/{ROT}/historial/        → estados de la rotación
   ```

## Casos que deben fallar (reglas de negocio)

- **RN-6** — internado con `fecha_fin` a más de 1 año de `fecha_inicio` (paso 3) → `400`.
- **RN-13** — crear internado sobre un campo clínico que ya alcanzó su `cantidad_maxima` → `400`.
- **RN-2/3/4** — `convenio` que no es Específico o no está vigente (paso 3) → `400`.
- **RN-8** — rotación con `ipress_origen`/`ipress_destino` de un ámbito distinto al del internado (paso 5) → `400`.
- **RN-9** — solicitar una 5.ª rotación para el mismo estudiante → `400`.
- **RN-11** — `iniciar` una rotación sin autorización `APROBADO` (saltarse el paso 6) → `400`.
- **RN-10** — `autorizar` con un `participante_convenio` que no es firmante del Convenio Específico → `400`.
- **Cross-tenant** — usuario de la Universidad A registra un estudiante de la Universidad B → `403`.

## Roles por endpoint

| Endpoint | Rol requerido |
|----------|---------------|
| `POST students/`, `tutors/` | Universidad o Administrador RENADS |
| `POST interns/`, `interns/{id}/rotaciones/`, `cambiar-tutor` | Universidad |
| `interns/{id}/cambiar-estado`, `rotations/{id}/cambiar-estado` | Administrador RENADS |
| `rotations/{id}/autorizar` | Autoridad de convenio |
| `rotations/{id}/iniciar` | Universidad |
| catálogos (GET) / lecturas | cualquier usuario autenticado (con alcance institucional) |

---

# Feature F1 — Periodo académico, declaraciones juradas y RN-19

Sección añadida tras validar la Feature F1. Cubre los endpoints nuevos `academic-periods` y `annex-documents`, las FKs `periodo_academico`/`especialidad` en `students`, la carga masiva con RN-19 y los filtros.

## Datos previos (F1)

- **Seedeados por migración** (existen tras `migrate`):
  - `academic-periods`: `2025-I`, `2025-II`, `2026-I`, `2026-II`.
  - `annex-documents`: `DJ_DATOS`, `DJ_ANTECEDENTES`, `DJ_SALUD`, `DJ_CONFIDENCIALIDAD` (todos `obligatorio: true`).
  - `nivel_academico`: `PREGRADO`, `SEGUNDA_ESPECIALIDAD`, `MAESTRIA`, `DOCTORADO`.
- **Obtener antes de crear estudiantes:** un `id` de carrera de nivel `PREGRADO` y uno de nivel distinto de Pregrado (`GET /api/v1/professional-careers/` expone `nivel_academico`); un `id` de especialidad (`GET /api/v1/specialties/`); un `id` de periodo (`GET /api/v1/academic-periods/`).

## 1. CRUD de catálogos nuevos

**Lectura (cualquier autenticado):**
```
GET /api/v1/academic-periods/         → 200 (2025-I, 2025-II, 2026-I, 2026-II)
GET /api/v1/annex-documents/          → 200 (DJ_DATOS, DJ_ANTECEDENTES, DJ_SALUD, DJ_CONFIDENCIALIDAD)
GET /api/v1/annex-documents/?obligatorio=true  → 200 (solo obligatorios)
```

**Crear (requiere rol `Administrador RENADS`):**
```
POST /api/v1/academic-periods/
{ "codigo": "2027-I", "nombre": "Semestre 2027-I", "activo": true }
→ 201
```
```
POST /api/v1/annex-documents/
{ "codigo": "DJ_SEGURO", "nombre": "DJ de seguro vigente",
  "descripcion": "El interno declara contar con seguro de salud vigente.",
  "obligatorio": true, "activo": true }
→ 201
```
**Caso que debe fallar (permiso):** el mismo `POST` con un usuario **sin** `Administrador RENADS`:
```
→ 403  "La escritura requiere el rol Administrador RENADS."
```

## 2. Estudiantes y RN-19 (rol `Universidad` o `Administrador RENADS`)

**2.1 PREGRADO con periodo (correcto → 201):**
```
POST /api/v1/students/
{ "tipo_documento_identidad": <DNI>, "numero_documento": "70000001",
  "nombres": "María", "apellido_paterno": "Quispe", "universidad": <UNI>,
  "carrera_profesional": <CARRERA_PREGRADO>, "periodo_academico": <PERIODO> }
→ 201   (guardar id = STUDENT_PREGRADO)
```

**2.2 Especialidad / nivel no-Pregrado (correcto → 201):**
```
POST /api/v1/students/
{ "tipo_documento_identidad": <DNI>, "numero_documento": "70000002",
  "nombres": "Jorge", "apellido_paterno": "Huamán", "universidad": <UNI>,
  "carrera_profesional": <CARRERA_MAESTRIA>, "especialidad": <ESPECIALIDAD> }
→ 201
```

**2.3 Casos RN-19 que deben fallar (400):**

a) PREGRADO sin `periodo_academico`:
```
POST /api/v1/students/  { ..., "carrera_profesional": <CARRERA_PREGRADO> }   (sin periodo)
→ 400  {"periodo_academico": ["El periodo académico es obligatorio para estudiantes de Pregrado."]}
```
b) PREGRADO con `especialidad` (sobrante):
```
POST /api/v1/students/  { ..., "carrera_profesional": <CARRERA_PREGRADO>,
                          "periodo_academico": <PERIODO>, "especialidad": <ESPECIALIDAD> }
→ 400  {"especialidad": ["La especialidad no aplica a estudiantes de Pregrado."]}
```
c) Nivel no-Pregrado sin `especialidad`:
```
POST /api/v1/students/  { ..., "carrera_profesional": <CARRERA_MAESTRIA> }   (sin especialidad)
→ 400  {"especialidad": ["La especialidad es obligatoria para este nivel académico."]}
```
d) Nivel no-Pregrado con `periodo_academico` (sobrante):
```
POST /api/v1/students/  { ..., "carrera_profesional": <CARRERA_MAESTRIA>,
                          "especialidad": <ESPECIALIDAD>, "periodo_academico": <PERIODO> }
→ 400  {"periodo_academico": ["El periodo académico solo aplica al nivel Pregrado."]}
```

**2.4 Update parcial (PATCH) — no exige reenviar campos ya guardados:**
```
PATCH /api/v1/students/<STUDENT_PREGRADO>/   { "telefono": "987654321" }
→ 200   (RN-19 se revalida con el periodo ya guardado en el instance; no hay que reenviarlo)

PATCH /api/v1/students/<STUDENT_PREGRADO>/   { "especialidad": <ESPECIALIDAD> }
→ 400   {"especialidad": ["La especialidad no aplica a estudiantes de Pregrado."]}
```

## 3. Filtros por los nuevos campos (lectura autenticada)
```
GET /api/v1/students/?periodo_academico=<PERIODO>    → 200 (incluye STUDENT_PREGRADO)
GET /api/v1/students/?especialidad=<ESPECIALIDAD>    → 200 (incluye el estudiante de 2.2)
```
Los resultados quedan acotados al ámbito institucional del usuario (RNF-SEG-04); un superusuario ve todo.

## 4. Carga masiva (bulk-upload) con RN-19 por fila (rol `Universidad`/`Administrador RENADS`)

Excel `.xlsx` (cabeceras en la primera fila) con columnas `periodo_academico` (código, p. ej. `2026-I`) y `especialidad` (código). Incluir una fila válida y una que viole RN-19 (p. ej. carrera Pregrado sin `periodo_academico`).
```
POST /api/v1/students/bulk-upload/
Content-Type: multipart/form-data
archivo=<estudiantes.xlsx>
→ 200
{ "creados": 1, "omitidos": 1,
  "errores": [ {"fila": 3, "motivo": "periodo_academico: El periodo académico es obligatorio para estudiantes de Pregrado."} ] }
```
La fila que viola RN-19 se reporta en `errores` con su número de fila y motivo, **sin** abortar el lote (las válidas se crean).

## 5. Verificación en Swagger (`/api/v1/docs/`)

Confirmar las operaciones CRUD de `/api/v1/academic-periods/`, `/api/v1/academic-periods/{id}/`, `/api/v1/annex-documents/`, `/api/v1/annex-documents/{id}/`, y que `/api/v1/students/` documenta los filtros `periodo_academico` y `especialidad`.

## Rol/permiso por endpoint (F1)

| Endpoint | Método | Rol requerido |
|----------|--------|----------------|
| `academic-periods/`, `annex-documents/` | GET | cualquier usuario autenticado |
| `academic-periods/`, `annex-documents/` | POST/PUT/PATCH/DELETE | `Administrador RENADS` |
| `students/` (crear/editar, `bulk-upload`) | POST/PUT/PATCH | `Universidad` o `Administrador RENADS` |
| `students/` (filtros por `periodo_academico`/`especialidad`) | GET | cualquier autenticado (con alcance institucional) |

---

# Guía de pruebas — Feature F2 (`annex-documents` por actor)

Sección añadida tras validar la Feature F2. El catálogo `annex-documents` se generalizó con el campo `tipo_actor` (`INTERNO` / `AUTORIDAD_UNIVERSIDAD` / `REPRESENTANTE`); el endpoint filtra por ese campo. Prerrequisitos y token JWT igual que en las secciones anteriores.

## Datos previos (F2)

Seedeados por migración (existen tras `migrate`), 8 registros en total:

| `tipo_actor` | Códigos | Cantidad |
|--------------|---------|----------|
| `INTERNO` | `DJ_DATOS`, `DJ_ANTECEDENTES`, `DJ_SALUD`, `DJ_CONFIDENCIALIDAD` | 4 |
| `AUTORIDAD_UNIVERSIDAD` | `RESOL_AUTUNI`, `DNI_AUTUNI` | 2 |
| `REPRESENTANTE` (incluye CONAPRES) | `RESOL_REP`, `DNI_REP` | 2 |

## 1. Filtro por `tipo_actor` (lectura, cualquier autenticado)
```
GET /api/v1/annex-documents/                              → 200 (8 registros)
GET /api/v1/annex-documents/?tipo_actor=INTERNO           → 200 (4: DJ_*)
GET /api/v1/annex-documents/?tipo_actor=AUTORIDAD_UNIVERSIDAD → 200 (2: RESOL_AUTUNI, DNI_AUTUNI)
GET /api/v1/annex-documents/?tipo_actor=REPRESENTANTE     → 200 (2: RESOL_REP, DNI_REP)
GET /api/v1/annex-documents/?tipo_actor=REPRESENTANTE&obligatorio=true → 200 (2)
```
Cada objeto expone `tipo_actor` en la respuesta (serializer `fields="__all__"`).

## 2. Crear documento por actor (requiere rol `Administrador RENADS`)
```
POST /api/v1/annex-documents/
{ "codigo": "RESOL_REP2", "nombre": "Resolución de designación (adjunta)",
  "descripcion": "Resolución que acredita el cargo del representante.",
  "tipo_actor": "REPRESENTANTE", "obligatorio": true, "activo": true }
→ 201   (tipo_actor persiste; recuperable con ?tipo_actor=REPRESENTANTE)
```
**Caso que debe fallar (permiso):** el mismo `POST` con un usuario **sin** `Administrador RENADS`:
```
→ 403  "La escritura requiere el rol Administrador RENADS."
```
**Caso que debe fallar (choice inválido):**
```
POST /api/v1/annex-documents/  { ..., "tipo_actor": "CONAPRES" }
→ 400  {"tipo_actor": ["\"CONAPRES\" no es una elección válida."]}
```
(Las autoridades de CONAPRES se registran con `tipo_actor="REPRESENTANTE"`; no existe un valor de actor propio para CONAPRES.)

## 3. Verificación en Swagger (`/api/v1/docs/`)

Confirmar que `GET /api/v1/annex-documents/` documenta el parámetro de query `tipo_actor` (enum `INTERNO`/`AUTORIDAD_UNIVERSIDAD`/`REPRESENTANTE`) y que el schema del cuerpo incluye el campo `tipo_actor`.

## Rol/permiso por endpoint (F2)

| Endpoint | Método | Rol requerido |
|----------|--------|----------------|
| `annex-documents/` (incl. `?tipo_actor=`) | GET | cualquier usuario autenticado |
| `annex-documents/` | POST/PUT/PATCH/DELETE | `Administrador RENADS` |

---

# Guía de pruebas manuales — Features F2 (adjunto real de anexos del interno) y F3 (onboarding)

## Prerrequisitos
1. Servidor: `python manage.py runserver` (lo corre el usuario). Base:
   `http://localhost:8000/api/v1/`. Swagger en `/api/v1/docs/`.
2. Token JWT de un usuario del rol `Universidad` con perfil sobre la universidad del
   estudiante (`POST /api/v1/auth/token/` → `Authorization: Bearer <access>`).
   El body de login ya incluye `debe_cambiar_password`, `grupos` y `es_superusuario`.
3. Correo en `dev`: `EMAIL_BACKEND` = consola; el correo de onboarding se imprime en la
   terminal donde corre `runserver`.

## Datos previos
- Un `Student` con `universidad` dentro del alcance del usuario y con `correo`
  registrado (para ver el correo de onboarding). `GET /api/v1/students/` → `id`.
- Un Convenio Específico vigente con un `campo_clinico` disponible, IPRESS, tutor y
  ámbito geográfico coherentes (ver la guía del núcleo de internados).
- Anexos `INTERNO` seedeados: `GET /api/v1/annex-documents/?tipo_actor=INTERNO`
  (algunos con `obligatorio=true`). Anota los `id`.

## Flujo F3 — Registro del interno, unicidad y onboarding

1. Registrar el internado (rol `Universidad`, alcance por universidad del estudiante):
   ```
   POST /api/v1/interns/
   {
     "estudiante": <id>, "convenio": <id_especifico>, "campo_clinico": <id>,
     "ipress": <id>, "tutor": <id>, "ambito_geografico_sanitario": <id>,
     "fecha_inicio": "2026-08-01", "fecha_fin": "2027-06-30"
   }
   ```
   Esperado: `201` con el internado en `estado_actual=REGISTRADO` y
   `estado_declaraciones="PENDIENTE"`. Efectos (RN-22):
   - Se crea el usuario `Interno` con `username = numero_documento` del estudiante,
     grupo `Interno`, perfil sobre su `Student` y `debe_cambiar_password=True`.
   - En la consola del servidor aparece el correo de onboarding con sede docente,
     campo clínico, fechas, tutor y los links de checklist/upload de DJ.

2. Caso RN-20 (fuera de alcance): con un token `Universidad` SIN perfil sobre la
   universidad del estudiante, repetir el paso 1 → `403`
   "...fuera del ámbito institucional..." (o el mensaje de `exigir_ambito`).

3. Caso RN-21 (unicidad, debe fallar): registrar un segundo internado para el mismo
   estudiante mientras su internado está en estado bloqueante (p. ej. `REGISTRADO`):
   ```
   POST /api/v1/interns/  (mismo estudiante)
   ```
   Esperado: `400` `{"estudiante": "El estudiante ya tiene un internado vigente; no puede registrarse otro."}`.

4. Caso RN-21 con estado liberador (debe permitir): pasar el internado previo a
   `SUSPENDIDO` (rol `Administrador RENADS`):
   ```
   POST /api/v1/interns/{id}/cambiar-estado/  {"estado_codigo": "SUSPENDIDO"}
   ```
   Luego repetir el registro del paso 1 → `201` (permitido). Igual para
   `RETIRADO`/`CULMINADO`/`ANULADO`.

## Flujo F2 — Adjunto real de declaraciones juradas del interno

5. Checklist del interno:
   ```
   GET /api/v1/students/{id}/annex-checklist/
   ```
   Esperado: `200` con los anexos `INTERNO` activos; inicialmente todos `adjuntado=false`.
   Rol: cualquier autenticado con alcance (Universidad/Administrador o el propio Interno).

6. Adjuntar cada DJ obligatoria (multipart). Rol `Universidad`/`Administrador` o el
   propio `Interno`:
   ```
   POST /api/v1/students/{id}/annex-upload/
   documento_anexo=<id de un anexo INTERNO>
   archivo=@declaracion.pdf
   ```
   Esperado: `201` con el `Document` (`version=1`, `estado="ACTIVO"`). Al completar
   TODAS las DJ `obligatorio=true`, el `estado_declaraciones` del internado pasa
   automáticamente de `PENDIENTE` a `COMPLETAS` (verificar con `GET /api/v1/interns/{id}/`).

7. Caso que debe fallar (actor no coincide): `documento_anexo` de `tipo_actor` distinto
   de `INTERNO` → `400` "El anexo seleccionado no corresponde a este tipo de actor."

8. Caso que debe fallar (no PDF): `archivo=@foto.png` → `400`
   "Tipo de archivo no permitido. El anexo debe adjuntarse en formato PDF."

9. Re-subir el mismo anexo → `201` con `version=2`; la anterior queda `REEMPLAZADO`.

## Flujo F3 — Revisión de DJ y gate RN-23

10. Revisar (rol `Universidad`/`Administrador RENADS`), estado debe ser `COMPLETAS`:
    ```
    POST /api/v1/interns/{id}/revisar-declaraciones/
    {"resultado": "OBSERVADAS", "observacion": "Falta firma en el anexo 2."}
    ```
    Esperado: `200`; `estado_declaraciones="OBSERVADAS"`. Al re-adjuntar y volver a
    cumplir el checklist, se recalcula a `COMPLETAS`.

11. Validar:
    ```
    POST /api/v1/interns/{id}/revisar-declaraciones/  {"resultado": "VALIDADAS"}
    ```
    Esperado: `200`; `estado_declaraciones="VALIDADAS"`.
    Caso que debe fallar: revisar cuando el estado NO es `COMPLETAS`/`OBSERVADAS`
    (p. ej. `PENDIENTE`) → `400` "Solo se pueden revisar declaraciones juradas en estado
    COMPLETAS u OBSERVADAS."

12. Gate RN-23 (activar internado):
    - Sin `VALIDADAS`:
      ```
      POST /api/v1/interns/{id}/cambiar-estado/  {"estado_codigo": "ACTIVO"}
      ```
      Esperado: `400` "El internado no puede pasar a ACTIVO hasta que sus declaraciones
      juradas estén VALIDADAS."
    - Con `estado_declaraciones="VALIDADAS"`: la misma llamada → `200`,
      `estado_actual="ACTIVO"`. Rol `Administrador RENADS`.

## Flujo F3 — Interno: acceso restringido y cambio de clave temporal

13. El usuario `Interno` obtiene token con su `username` (= DNI). El body de login
    incluye `"debe_cambiar_password": true`.

14. Cambiar la clave temporal:
    ```
    POST /api/v1/auth/me/cambiar-password/
    {"password_actual": "<temporal>", "password_nueva": "<nueva-segura>"}
    ```
    Esperado: `200`; en `GET /api/v1/auth/me/` el flag `debe_cambiar_password=false`.
    Caso que debe fallar: `password_actual` incorrecta → `400`
    "La contraseña actual no es correcta."; `password_nueva` débil → `400` (validadores Django).

15. Alcance del `Interno`:
    - `GET /api/v1/students/{su_id}/` → `200` (solo lectura de sus datos).
    - `GET /api/v1/students/{otro_id}/` → `404` (fuera de su alcance).
    - `PATCH /api/v1/students/{su_id}/` → `403` (no puede editar datos personales).
    - `POST /api/v1/students/{su_id}/annex-upload/` y `GET .../annex-checklist/` → permitidos.

## Roles por endpoint (resumen)
- `POST /interns/` (registro): `Universidad` + alcance por universidad del estudiante.
- `POST /interns/{id}/revisar-declaraciones/`: `Universidad` o `Administrador RENADS`.
- `POST /interns/{id}/cambiar-estado/`: `Administrador RENADS` (gate RN-23 aplica).
- `POST /students/{id}/annex-upload/`, `GET .../annex-checklist/`: `Universidad`/
  `Administrador RENADS` (con alcance) o el propio `Interno`.
- `POST /auth/me/cambiar-password/`: cualquier usuario autenticado (sobre sí mismo).
