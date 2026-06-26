# API — Módulo 3: Registrar Actividades (`apps/actividades`)

Registro, validación y consulta de actividades docente-asistenciales de internos en sedes.
Módulo pequeño: 2 catálogos + `TeachingActivity`. Reutiliza módulos 1 y 2
(`Intern`, `Internship`, `Rotation`, `Tutor`, `Ipress`, `ServiceArea`). Base: `/api/v1/`. JWT requerido.

## Reglas de negocio clave

- **RN-1:** el `internado` debe estar **activo** para registrar actividad.
- **RN-2:** `fecha_actividad` dentro de `[internado.fecha_inicio, internado.fecha_fin]`.
- **RN-3/4:** si se envía `rotacion`, debe pertenecer al internado y estar `AUTORIZADA`/`EN_CURSO`.
- **RN-7:** subsanar solo si la actividad está `OBSERVADA` → pasa a `SUBSANADA`.
- **RN-8:** una actividad `VALIDADA` no se modifica sin trazabilidad.
- **RN-9:** no duplicar por (`interno`, `fecha_actividad`, `ipress`, `servicio_area`).

## `teaching-activities`

| Método | Ruta | Rol | Notas |
|--------|------|-----|-------|
| GET | `/teaching-activities/` , `/{id}/` | autenticado (alcance) | filtros abajo |
| POST | `/teaching-activities/` | `Universidad` / `Tutor` / `Sede docente` | estado inicial `REGISTRADA` |
| PUT/PATCH | `/teaching-activities/{id}/` | alcance | solo `descripcion, carga_horaria, tipo_actividad, servicio_area` |
| POST | `/teaching-activities/{id}/validar/` | `Tutor` | `{ resultado, comentario? }` |
| POST | `/teaching-activities/{id}/subsanar/` | `Universidad` / `Tutor` / `Sede docente` | `{ descripcion?, carga_horaria? }` |
| POST | `/teaching-activities/{id}/cambiar-estado/` | `Administrador RENADS` | `{ estado_codigo, observacion? }` |
| GET | `/teaching-activities/{id}/historial/` | autenticado | |

`validar.resultado` ∈ `VALIDADA` | `OBSERVADA` | `RECHAZADA`.

**Filtros** (`TeachingActivityFilter`): `interno`, `internado`, `ipress`, `tutor`, `rotacion`,
`tipo_actividad`, `estado_actual`, rango de `fecha_actividad`. **Search:** `descripcion`.
**Ordering:** `fecha_actividad`, `id`.

### TeachingActivity — lectura
```
id, interno, internado, ipress, rotacion, tutor, servicio_area, tipo_actividad,
estado_actual, estado_codigo, fecha_actividad, descripcion, carga_horaria,
creado_por, creado_en, actualizado_en
```
### TeachingActivity — escritura (POST)
```
interno, internado, ipress, rotacion, tutor, servicio_area,
tipo_actividad, fecha_actividad, descripcion, carga_horaria
```

## Catálogos (solo lectura)

`activity-types`, `activity-statuses` (estados: `REGISTRADA`, `VALIDADA`, `OBSERVADA`,
`SUBSANADA`, `RECHAZADA`, `CERRADA`, ...).

## Alcance

Visible/editable si el interno pertenece a la **universidad** del usuario o la actividad ocurre
en una **IPRESS (sede)** de su ámbito. Superusuario y `Administrador RENADS` ven todo.
