# API — Módulo 2: Registrar Internados (`apps/internados`)

Internos, tutores, internados, rotaciones y autorizaciones. Reutiliza modelos del módulo 1
(`Convention`, `ClinicalField`, `Ipress`, `University`, `ConventionParticipant`).
Base: `/api/v1/`. JWT requerido.

## Reglas de negocio clave

- **RN-2/3/4:** un internado solo se registra sobre **Convenio Específico vigente**
  (`VIGENTE`/`PUBLICADO`/`SUSCRITO`); nunca sobre Marco.
- **RN-5:** `tutor` obligatorio al crear.
- **RN-6:** duración del internado ≤ 1 año.
- **RN-8:** una rotación va entre IPRESS del **mismo ámbito geográfico sanitario** del internado.
- **RN-9:** máximo **4 rotaciones** por interno.
- **RN-10:** autorizar rotación solo una **autoridad firmante** del Convenio Específico.
- **RN-11:** una rotación no inicia sin autorización aprobada.
- **RN-14:** cambio de tutor queda registrado en historial (`TutorHistory`).

## `internships`

| Método | Ruta | Rol | Notas |
|--------|------|-----|-------|
| GET | `/internships/` | autenticado (alcance) | filtros abajo |
| GET | `/internships/{id}/` | autenticado (alcance) | |
| POST | `/internships/` | `Universidad` | estado inicial `REGISTRADO` |
| PUT/PATCH | `/internships/{id}/` | alcance | solo `ipress, observaciones, fecha_inicio, fecha_fin` |
| POST | `/internships/{id}/cambiar-estado/` | `Administrador RENADS` | `{ estado_codigo, observacion? }` |
| POST | `/internships/{id}/cambiar-tutor/` | `Universidad` | `{ tutor, fecha_cambio, motivo }` |
| GET | `/internships/{id}/historial/` | autenticado | historial de estados |
| GET·POST | `/internships/{id}/rotaciones/` | POST: `Universidad` | GET lista / POST crea rotación |

**Filtros** (`InternshipFilter`): `convenio`, `ipress`, `tutor`, `estado_actual`,
`ambito_geografico_sanitario`, rangos de fecha. **Search:** documento/nombres del interno.
**Ordering:** `fecha_inicio`, `fecha_fin`, `id`.

### Internship — lectura
```
id, interno, convenio, campo_clinico, ipress, tutor, ambito_geografico_sanitario,
estado_actual, estado_codigo, fecha_inicio, fecha_fin, observaciones,
creado_por, creado_en, actualizado_en
```
### Internship — escritura (POST)
```
interno, convenio, campo_clinico, ipress, tutor,
ambito_geografico_sanitario, fecha_inicio, fecha_fin, observaciones
```
### Crear rotación (POST `/rotaciones/`)
```
ipress_origen, ipress_destino, servicio_area, fecha_inicio, fecha_fin, observaciones
```

## `rotations` (lectura + acciones)

| Método | Ruta | Rol | Notas |
|--------|------|-----|-------|
| GET | `/rotations/` , `/rotations/{id}/` | autenticado (alcance) | filtros: `internado`, `estado_actual`, `ipress_origen`, `ipress_destino`, `servicio_area` |
| POST | `/rotations/{id}/autorizar/` | `Autoridad de convenio` | `{ participante_convenio, resultado, fecha_autorizacion, observaciones }` |
| POST | `/rotations/{id}/iniciar/` | `Universidad` | requiere autorización aprobada → `EN_CURSO` |
| POST | `/rotations/{id}/cambiar-estado/` | `Administrador RENADS` | `{ estado_codigo, observacion? }` |
| GET | `/rotations/{id}/historial/` | autenticado | |

### Rotation — lectura
```
id, internado, numero_rotacion, ipress_origen, ipress_destino, servicio_area,
estado_actual, estado_codigo, fecha_inicio, fecha_fin, observaciones, creado_por, creado_en
```
Estados de rotación: `SOLICITADA`, `AUTORIZADA`, `OBSERVADA`, `RECHAZADA`, `EN_CURSO`, ... (catálogo `rotation-statuses`).

## Personas (CRUD) — escritura `Universidad` / `Administrador RENADS`

- `interns` — filtros `universidad`, `carrera_profesional`, `especialidad`, `numero_documento`, `activo`; search documento/nombres. Alcance por universidad.
- `tutors` — filtros `especialidad`, `ipress`, `numero_documento`, `activo`.

## Catálogos (solo lectura)

`internship-statuses`, `rotation-statuses`, `service-areas`, `identity-document-types`.
