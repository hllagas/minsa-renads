# API — Módulo 2: Registrar Internados (`apps/internados`)

Estudiantes, tutores, internos (proceso de internado), rotaciones y autorizaciones.
Reutiliza modelos del módulo 1 (`Convention`, `ClinicalField`, `Ipress`, `University`,
`ConventionParticipant`). Base: `/api/v1/`. JWT requerido.

> **Terminología (contrato vigente):** `estudiante` = la persona (antes "interno");
> `interno` = el registro del proceso de internado (antes "internado").
> Rutas renombradas: `/internships/` → `/interns/` y `/interns/` → `/students/`.

## Reglas de negocio clave

- **RN-2/3/4:** un interno solo se registra sobre **Convenio Específico vigente**
  (`VIGENTE`/`PUBLICADO`/`SUSCRITO`); nunca sobre Marco.
- **RN-5:** `tutor` obligatorio al crear.
- **RN-6:** duración del internado ≤ 1 año.
- **RN-8:** una rotación va entre IPRESS del **mismo ámbito geográfico sanitario** del interno.
- **RN-9:** máximo **4 rotaciones** por interno.
- **RN-10:** autorizar rotación solo una **autoridad firmante** del Convenio Específico.
- **RN-11:** una rotación no inicia sin autorización aprobada.
- **RN-14:** cambio de tutor queda registrado en historial (`TutorHistory`).

## `interns` (proceso de internado)

| Método | Ruta | Rol | Notas |
|--------|------|-----|-------|
| GET | `/interns/` | autenticado (alcance) | filtros abajo |
| GET | `/interns/{id}/` | autenticado (alcance) | |
| POST | `/interns/` | `Universidad` | estado inicial `REGISTRADO` |
| PUT/PATCH | `/interns/{id}/` | alcance | solo `ipress, observaciones, fecha_inicio, fecha_fin` |
| POST | `/interns/{id}/cambiar-estado/` | `Administrador RENADS` | `{ estado_codigo, observacion? }` |
| POST | `/interns/{id}/cambiar-tutor/` | `Universidad` | `{ tutor, fecha_cambio, motivo }` |
| GET | `/interns/{id}/historial/` | autenticado | historial de estados |
| GET·POST | `/interns/{id}/rotaciones/` | POST: `Universidad` | GET lista / POST crea rotación |

**Filtros** (`InternshipFilter`): `convenio`, `ipress`, `tutor`, `estado_actual`,
`ambito_geografico_sanitario`, `estudiante`, rangos de fecha. **Search:** documento/nombres
del estudiante. **Ordering:** `fecha_inicio`, `fecha_fin`, `id`.

> **UI (2026-09-09):** la lista de internos exige elegir **universidad** (acotada al alcance) y luego
> un **convenio Específico vigente** de esa universidad (combo `conventions` filtrado por
> `universidad` + `tipo_convenio`=Específico + `estado_actual`=Vigente); el listado se filtra por
> `convenio`. El gate de universidad es `components/internados/university-gate.tsx` (`useUniversityGate`).

### Intern (internado) — lectura
```
id, estudiante, convenio, campo_clinico, ipress, tutor, ambito_geografico_sanitario,
estado_actual, estado_codigo, estado_declaraciones,
fecha_inicio, fecha_fin, observaciones, creado_por, creado_en, actualizado_en
```
### Intern (internado) — escritura (POST)
```
estudiante, convenio, campo_clinico, ipress, tutor,
ambito_geografico_sanitario, fecha_inicio, fecha_fin, observaciones
```
> **Refactor 2026-09-09 (mig 0025):** el **contacto de emergencia** se movió del internado al
> **estudiante** (revierte 0015). El internado ya NO expone/acepta `contacto_emergencia_*`; ahora
> viven en `students` (opcionales; `contacto_emergencia_parentesco` FK a `relationship-types`).
### Crear rotación (POST `/rotaciones/`)
```
ipress_origen, ipress_destino, servicio_area, fecha_inicio, fecha_fin, observaciones
```

## `rotations` (lectura + acciones)

| Método | Ruta | Rol | Notas |
|--------|------|-----|-------|
| GET | `/rotations/` , `/rotations/{id}/` | autenticado (alcance) | filtros: `interno`, `estado_actual`, `ipress_origen`, `ipress_destino`, `servicio_area` |
| POST | `/rotations/{id}/autorizar/` | `Autoridad de convenio` | `{ participante_convenio, resultado, fecha_autorizacion, observaciones }` |
| POST | `/rotations/{id}/iniciar/` | `Universidad` | requiere autorización aprobada → `EN_CURSO` |
| POST | `/rotations/{id}/cambiar-estado/` | `Administrador RENADS` | `{ estado_codigo, observacion? }` |
| GET | `/rotations/{id}/historial/` | autenticado | |

### Rotation — lectura
```
id, interno, numero_rotacion, ipress_origen, ipress_destino, servicio_area,
estado_actual, estado_codigo, fecha_inicio, fecha_fin, observaciones, creado_por, creado_en
```
Estados de rotación: `SOLICITADA`, `AUTORIZADA`, `OBSERVADA`, `RECHAZADA`, `EN_CURSO`, ... (catálogo `rotation-statuses`).

## Personas (CRUD) — escritura `Universidad` / `Administrador RENADS`

- `students` (estudiantes) — filtros `universidad`, `carrera_profesional`, `numero_documento`,
  `activo`, y **`nivel_academico`** (refactor 2026-09-09: `StudentFilter` filtra por
  `carrera_profesional__nivel_academico` — el estudiante NO persiste el nivel, deriva de la carrera).
  Search documento/nombres. Alcance por universidad. Lectura expone **`carrera_profesional_detalle`**
  (`{id, nombre, nivel_academico}`) y **`especialidad_detalle`** (`{id, nombre}`). Incluye
  `periodo_internado` (renombrado desde `periodo_academico`, mig 0028; endpoint `internship-periods`) y `especialidad` (FK opcionales, validadas por nivel académico — RN-19) y
  `nota_promedio_ponderado` (decimal 0–20, usado por el backend para la prelación RN-18 — sin
  endpoint propio). **Contacto de emergencia (mig 0025, 2026-09-09):** `contacto_emergencia_nombre`,
  `contacto_emergencia_telefono`, `contacto_emergencia_parentesco` (FK `relationship-types`) viven
  ahora en el **estudiante** (se movieron del internado). **UI (2026-09-09):** la vista exige elegir
  universidad (acotada al alcance) antes de listar; el form fija la universidad (oculta) y usa un
  nivel **virtual** que alterna carrera↔especialidad; el filtro de nivel arranca en «Pregrado». Ver
  `spec/estudiantes.md`.
- `tutors` — filtros `universidades`, `activo`; search documento/nombres. `universidades` es M2M
  de 1 a 2 (RN-24); conserva `especialidad`, `ipress`, `numero_colegiatura`, `ubigeo`. **Gana
  `profesion`** (FK `professional-careers`, opcional — mig 0025, 2026-09-09). Lectura expone
  `profesion_detalle`/`ipress_detalle`/`especialidad_detalle` (`{id, nombre}`). **UI (2026-09-09):**
  la vista exige elegir universidad (acotada al alcance) antes de listar (filtro `universidades`);
  columnas = N° colegiatura / apellidos+nombres / profesión / sede docente; el form incluye `ubigeo`.

### TutorConvenio — vínculo tutor × convenio × IPRESS

Cada tutor puede estar asignado a uno o varios **Convenios Específicos + IPRESS** (tabla `tutor_convenio`).
Escritura: `Universidad` / `Administrador RENADS`.

| Método | Ruta | Notas |
|--------|------|-------|
| GET | `/tutors/{id}/convenios/` | Lista todos los `TutorConvenio` del tutor |
| POST | `/tutors/{id}/convenios/` | Crea un vínculo nuevo |
| GET | `/tutors/{id}/convenios/{convenio_pk}/` | Detalle de un vínculo |
| DELETE | `/tutors/{id}/convenios/{convenio_pk}/` | Elimina el vínculo (204) |

**Escritura (POST):**
```
convenio (req — Convenio Específico vigente), ipress (req — IPRESS del convenio)
```

**Lectura (GET):**
```
id (convenio_pk), tutor, convenio, convenio_detalle {id, titulo, nomenclatura},
ipress, ipress_detalle {codigo_renipress, nombre}
```

> **RN:** solo Convenios Específicos vigentes (`VIGENTE`/`PUBLICADO`/`SUSCRITO`). La IPRESS debe
> pertenecer al ámbito del convenio (validado en backend — 400 si no). Un tutor puede tener
> múltiples vínculos con distintos convenios; no hay unicidad por convenio (puede asignarse a
> varias IPRESS del mismo convenio).

### Carga masiva de estudiantes — RN-16

- **`POST /students/bulk-upload/`** — rol `Universidad` / `Administrador RENADS`.
  `multipart/form-data` con campo **`archivo`** (Excel `.xlsx`). Alcance validado por fila.
- Columnas requeridas (cabecera de la hoja): `tipo_documento` (código, p. ej. `DNI`),
  `numero_documento`, `nombres`, `apellido_paterno`, `universidad` (id o `codigo_inei`),
  `carrera_profesional` (id o nombre, de la universidad indicada). Filas inválidas se
  reportan sin abortar el lote.
- Respuesta 200: `{ "creados": n, "omitidos": n, "errores": [{ "fila": n, "motivo": "..." }] }`.

## Catálogos (solo lectura)

`internship-statuses`, `rotation-statuses`, `service-areas`, `identity-document-types`,
`relationship-types` (parentesco del contacto de emergencia).

## Coordinadores (`coordinators`) — escritura `Universidad` / `Administrador RENADS`

Coordinadores de tutores por sede docente. Un coordinador puede ser también tutor (FK
opcional y única — RN-CRD-02). Puede representar múltiples sedes sin límite (RN-CRD-03).

| Método | Ruta | Rol | Notas |
|--------|------|-----|-------|
| GET | `/coordinators/` | autenticado (alcance) | filtros abajo |
| GET | `/coordinators/{id}/` | autenticado | |
| POST | `/coordinators/` | `Universidad` / `Admin RENADS` | |
| PATCH / DELETE | `/coordinators/{id}/` | `Universidad` / `Admin RENADS` | |
| GET / POST | `/coordinators/{id}/sedes/` | GET: autenticado; POST: `Universidad` / `Admin RENADS` | Agregar sede (RN-CRD-04/05) |
| GET / DELETE | `/coordinators/{id}/sedes/{sede_pk}/` | GET: autenticado; DELETE: `Universidad` / `Admin RENADS` | CASCADE elimina tutores |
| GET / POST | `/coordinators/{id}/sedes/{sede_pk}/tutores/` | GET: autenticado; POST: `Universidad` / `Admin RENADS` | Asignar tutor (RN-CRD-06) |
| DELETE | `/coordinators/{id}/sedes/{sede_pk}/tutores/{tutor_pk}/` | `Universidad` / `Admin RENADS` | Desasignar tutor |
| GET | `/coordinators/{id}/sedes-disponibles/` | autenticado | IPRESS aptas para asignar al coordinador |

**Filtros** (`CoordinatorFilter`): `activo`, `universidad`, `sedes__ipress`.
**Search:** `nombres`, `apellido_paterno`, `numero_documento`.

### Coordinator — lectura
```
id, tutor (FK nullable), tutor_detalle {id, nombres, apellido_paterno},
universidad (FK req), universidad_detalle {id, nombre},
tipo_documento_identidad, numero_documento,
nombres, apellido_paterno, apellido_materno,
correo, telefono, numero_colegiatura, direccion,
ubigeo, especialidad, profesion, activo
```

### Coordinator — escritura (POST/PATCH)
```
tutor (nullable), universidad (req), tipo_documento_identidad, numero_documento,
nombres, apellido_paterno, apellido_materno,
correo, telefono, numero_colegiatura, direccion,
ubigeo, especialidad, profesion, activo
```

### CoordinatorSede — lectura
```
id, coordinador, ipress,
universidad_detalle {id, nombre},   (derivada de coordinador.universidad — mig 0033)
ipress_detalle {codigo_renipress, nombre}
```

### CoordinatorSede — escritura (POST)
```
ipress (req — código RENIPRESS, es_sede_docente=True, RN-CRD-04/05)
```
> Desde la migración 0033, `CoordinatorSede` ya no tiene campo `universidad` propio.
> La universidad se deriva automáticamente del coordinador al que pertenece la sede.

### CoordinatorSede — sedes disponibles
```
GET /coordinators/{id}/sedes-disponibles/
Devuelve [{id: codigo_renipress, nombre}] — IPRESS con es_sede_docente=True,
con ≥1 Convenio Específico vigente para la universidad del coordinador y
que no están ya asignadas al coordinador.
```

### CoordinatorTutor — lectura
```
id, coordinador_sede, tutor,
tutor_detalle {id, nombres, apellido_paterno, numero_documento}
```

### CoordinatorTutor — escritura (POST)
```
tutor (req — id numérico; unicidad global por sede+universidad validada en backend — RN-CRD-06)
```
