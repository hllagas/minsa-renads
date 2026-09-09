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
  `periodo_academico` y `especialidad` (FK opcionales, validadas por nivel académico — RN-19) y
  `nota_promedio_ponderado` (decimal 0–20, usado por el backend para la prelación RN-18 — sin
  endpoint propio). **Contacto de emergencia (mig 0025, 2026-09-09):** `contacto_emergencia_nombre`,
  `contacto_emergencia_telefono`, `contacto_emergencia_parentesco` (FK `relationship-types`) viven
  ahora en el **estudiante** (se movieron del internado). **UI (2026-09-09):** la vista exige elegir
  universidad (acotada al alcance) antes de listar; el form fija la universidad (oculta) y usa un
  nivel **virtual** que alterna carrera↔especialidad; el filtro de nivel arranca en «Pregrado». Ver
  `spec/estudiantes.md`.
- `tutors` — filtros `universidades`, `activo`; search documento/nombres. `universidades` es M2M
  de 1 a 2 (RN-24); conserva `especialidad`, `ipress`, `numero_colegiatura`. **Gana `profesion`**
  (FK `professional-careers`, opcional — mig 0025, 2026-09-09).

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
