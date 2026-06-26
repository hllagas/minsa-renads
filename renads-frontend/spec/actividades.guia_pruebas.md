# Guía de pruebas manuales — Módulo `actividades`

Prueba registro, validación, subsanación y consulta de actividades docente-asistenciales.

## Prerrequisitos
1. **Backend** (`python manage.py runserver`) y **frontend** (`npm run dev`) arriba (los corre el usuario).
2. Sesión iniciada. Registrar → `Universidad`/`Tutor`/`Sede docente`; validar → `Tutor`;
   cambiar estado → `Administrador RENADS`.
3. **Datos base** (crear si el backend no los tiene): `activity-types` (tipos de actividad), un
   **internado activo** con su interno, tutor, IPRESS y `service-areas`. (Ver guías de Convenios e Internados.)

## 1. Lista (`/actividades`)
1. Abrir `/actividades` → tabla (interno, sede, tipo, estado, fecha).
2. **Búsqueda** por descripción; **filtros** por tipo y estado (combobox server-side); paginación.

## 2. Registrar actividad (`/actividades/nueva`)
1. "Nueva actividad" (rol Universidad/Tutor/Sede docente).
2. Seleccionar **Interno**, **Internado**, **IPRESS**, **Tutor**, **Servicio/área**, **Tipo de
   actividad** (combobox); **Rotación** opcional; **Fecha**; descripción; carga horaria.
3. Guardar → redirige al detalle. Casos que deben **fallar** (toast con error del backend):
   - Internado **no activo** (RN-1).
   - `fecha_actividad` fuera del periodo del internado (RN-2).
   - Duplicado por (interno, fecha, ipress, servicio_area) (RN-9).

## 3. Detalle (`/actividades/[id]`)
1. Pestaña **Datos**: interno, sede, tutor, tipo, estado (`estado_actual` + código), fecha, carga, descripción.
2. **Editar** → descripción/carga/tipo/servicio (PATCH). Una actividad `VALIDADA` no debería poder
   modificarse (RN-8: el backend lo impide).
3. Pestaña **Historial**: transiciones de estado.

## 4. Flujo (acciones por rol)
| Acción | Rol | Esperado |
|--------|-----|----------|
| Validar | Tutor | resultado Validada/Observada/Rechazada (+comentario) → cambia el estado |
| Subsanar | Universidad/Tutor/Sede docente | solo si está **Observada** (RN-7) → pasa a Subsanada |
| Cambiar estado | Administrador RENADS | `{estado_codigo, observacion}` |

Pasos: botón → completar diálogo → Guardar → toast de éxito; el estado/historial se refresca.
Verificar que un usuario **sin** el rol **no ve** el botón.

## Notas / limitaciones
- `tipo_actividad` en edición arranca vacío (el read da el nombre, no el id); se reasigna solo si se cambia.
- El gating del front es UX; el backend valida rol, RN (internado activo, periodo, rotación, duplicidad) y estados.
- Si `activity-types` u otros datos base están vacíos, crearlos antes de registrar actividades.
