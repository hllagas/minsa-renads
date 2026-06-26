# Guía de pruebas manuales — Módulo `actividades`

Generada por el agente **validator** tras validación exitosa.

## Prerrequisitos
1. Servidor: `python manage.py runserver`. Base: `http://localhost:8000/api/v1/`. Swagger: `/api/v1/docs/`.
2. **Token JWT:** `POST /api/v1/auth/token/` → header `Authorization: Bearer <access>`.
3. **Roles:** `Universidad`/`Tutor`/`Sede docente` (registrar y subsanar), `Tutor` (validar), `Administrador RENADS` (cambiar estado). Atajo camino feliz: superusuario.
4. **Datos previos:** un **internado en estado `ACTIVO`** (módulos 1–2), con su `interno`, `ipress`, `tutor`. Catálogos: `activity-statuses` (7, seedeado), `activity-types` (crear vía `/admin/` o seed — no editable por API), `service-areas` (crear en `/api/v1/service-areas/`... es solo lectura; crear por `/admin/` o shell).

> Nota: `activity-types` y `service-areas` son catálogos de **solo lectura** vía API. Crear sus valores en `/admin/` o `manage.py shell` antes de probar (o seedearlos).

## Flujo paso a paso

1. **Registrar actividad** (rol `Universidad`/`Tutor`/`Sede docente`; el internado debe estar `ACTIVO`):
   ```
   POST /api/v1/teaching-activities/
   { "interno": <id>, "internado": <id ACTIVO>, "ipress": <id>, "tutor": <id>,
     "servicio_area": <id>, "tipo_actividad": <id>, "fecha_actividad": "2026-05-01",
     "descripcion": "Atención en emergencia", "carga_horaria": "6.00" }
   → 201  estado_codigo="REGISTRADA"   (guardar id = ACT)
   ```
   (Opcional `"rotacion": <id>` si la actividad ocurre en una rotación; debe estar `AUTORIZADA`/`EN_CURSO`.)
2. **Validar actividad — observar** (rol `Tutor`):
   ```
   POST /api/v1/teaching-activities/{ACT}/validar/
   { "resultado": "OBSERVADA", "comentario": "Falta detalle de procedimientos" }
   → 200  estado_codigo="OBSERVADA"
   ```
3. **Subsanar** (rol `Universidad`/`Tutor`/`Sede docente`):
   ```
   POST /api/v1/teaching-activities/{ACT}/subsanar/
   { "descripcion": "Atención en emergencia: 3 procedimientos detallados" }
   → 200  estado_codigo="SUBSANADA"
   ```
4. **Validar — aprobar** (rol `Tutor`):
   ```
   POST /api/v1/teaching-activities/{ACT}/validar/
   { "resultado": "VALIDADA" }
   → 200  estado_codigo="VALIDADA"
   ```
5. **Consultar historial:**
   ```
   GET /api/v1/teaching-activities/{ACT}/historial/
   → 200 (REGISTRADA → OBSERVADA → SUBSANADA → VALIDADA)
   ```
6. **Listar/filtrar:**
   ```
   GET /api/v1/teaching-activities/?internado=<id>&estado_actual=<id>&fecha_desde=2026-05-01
   → 200 (solo actividades del ámbito del usuario)
   ```

## Casos que deben fallar (reglas de negocio)
- **RN-1** — registrar con un internado **no** `ACTIVO` → `400`.
- **RN-2** — `fecha_actividad` fuera de `[internado.fecha_inicio, fecha_fin]` → `400`.
- **RN-3/4** — `rotacion` que no pertenece al internado o no está `AUTORIZADA`/`EN_CURSO` → `400`.
- **RN-9** — registrar dos veces con mismo `interno`+`fecha_actividad`+`ipress`+`servicio_area` → `400`.
- **RN-8** — `PATCH` a una actividad ya `VALIDADA` → `400`.
- **Cross-tenant** — usuario fuera del ámbito (ni universidad del interno ni la sede) registra/accede → `403`.

## Roles por endpoint
| Endpoint | Rol |
|----------|-----|
| `POST teaching-activities/`, `subsanar` | Universidad / Tutor / Sede docente |
| `validar` | Tutor |
| `cambiar-estado` | Administrador RENADS |
| `historial`, listados (GET) | autenticado (con alcance institucional) |
| `activity-types`, `activity-statuses` (GET) | autenticado |
