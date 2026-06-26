# Alcance del MVP — RENADS API

Define el alcance del producto mínimo viable (MVP), la metodología de trabajo y el despliegue. Complementa el [schema de base de datos](db_schema_er_global.md) y la [arquitectura de desarrollo](arquitectura_desarrollo.md).

---

## 1. Objetivo del MVP

Entregar un API REST funcional que permita gestionar los tres módulos de RENADS con operaciones **CRUD** básicas por cada entidad, autenticación con JWT sobre el sistema de usuarios de Django, y despliegue en **Railway**.

---

## 2. Alcance funcional

### Módulos (cada uno es una app Django dentro de `apps/`)

| Módulo | App | Alcance MVP |
|--------|-----|-------------|
| Gestionar Convenios | `apps.convenios` | CRUD de convenios, plantillas, participantes, campos clínicos, evaluaciones/opiniones/firmas/publicaciones, catálogos |
| Registrar Internados | `apps.internados` | CRUD de internos, tutores, internados, rotaciones, autorizaciones |
| Registrar Actividades | `apps.actividades` | CRUD de actividades docente-asistenciales y validaciones |

### CRUD por entidad
Para cada entidad relevante del módulo: **listar, obtener, crear, actualizar, eliminar** vía DRF `ModelViewSet`, con paginación, filtros y permisos. Las reglas de negocio (validaciones RN) se aplican en la capa de **services** según la arquitectura.

### Catálogos
Expuestos como solo lectura (ya seedeados por data migrations).

---

## 3. Autenticación y autorización

- **Base:** sistema de autenticación de Django (`auth.User`, `auth.Group`, `auth.Permission`).
- **Tokens:** **JWT** con `djangorestframework-simplejwt` — `POST /api/v1/auth/token/` y `/api/v1/auth/token/refresh/`.
- **Roles:** grupos de Django; **alcance institucional** vía `perfil_usuario_entidad`.
- **Por defecto:** todos los endpoints requieren autenticación (`IsAuthenticated`) salvo el login.

---

## 4. Despliegue — Railway

- **Base de datos:** PostgreSQL gestionado por Railway; conexión vía `DATABASE_URL` (con `dj-database-url`).
- **Servidor:** `gunicorn` (`gunicorn config.wsgi`).
- **Estáticos:** `whitenoise` + `collectstatic` en el build.
- **Configuración por entorno** (variables de Railway): `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, parámetros JWT y del repositorio externo de archivos.
- **Migraciones:** ejecutar `migrate` en el release/deploy (incluye el seed de catálogos).
- **Archivos:** los adjuntos no se guardan en Railway; van al repositorio externo (`DocumentStorage`).
- **Dependencias a agregar:** `djangorestframework-simplejwt`, `drf-spectacular`, `django-filter`, `dj-database-url`, `gunicorn`, `whitenoise`.

---

## 5. Fuera de alcance del MVP

Notificaciones/alertas, reportes y exportación PDF/Excel, analítica, integraciones externas (RENIEC/SUNEDU), firma digital propia, y **archivos de testing automatizado** (en esta etapa la verificación es por revisión de código, no por suite de tests).

---

## 6. Metodología — SDD (Spec Driven Development)

El desarrollo sigue **Spec Driven Development**: primero se especifican tareas exactas por módulo, luego se implementan, y finalmente se validan contra la especificación. Lo conduce un equipo de 4 agentes en `.claude/agents/`:

| Agente | Rol | Escribe código | Salida |
|--------|-----|----------------|--------|
| **Orchestrator** | Coordina el flujo Spec → Implement → Validate; no escribe código ni specs | No | Instrucciones de flujo |
| **Spec** | Analiza requerimientos y crea la lista de tareas exactas por módulo | No (solo specs) | `spec/<modulo>.md` |
| **Implement** | Desarrolla el código según las tareas, la arquitectura y el schema | Sí | Código en `apps/<modulo>/` |
| **Validator** | Revisa lo implementado contra requerimientos, arquitectura y schema | No | `spec/<modulo>.validacion.md` o confirmación |

### Flujo obligatorio

```
Orchestrator
   │
   ├─1─► Spec       → genera spec/<modulo>.md (tareas exactas)
   │
   ├─2─► Implement  → lee spec/<modulo>.md, escribe código en apps/<modulo>/
   │
   └─3─► Validator  → revisa código vs spec/arquitectura/schema
            │
            ├─ con errores → spec/<modulo>.validacion.md → vuelve a Implement
            └─ sin errores → confirmación → módulo cerrado
```

- **Fuente de verdad:** los documentos en `docs/` (schema por módulo, ER global, arquitectura) y los specs en `spec/`.
- Cada módulo se cierra solo cuando el Validator confirma sin errores.
- El Orchestrator está referenciado en `CLAUDE.md` para aplicarse en cada solicitud de desarrollo.

### Carpeta `spec/`
Contiene un archivo de tareas por módulo (`spec/convenios.md`, `spec/internados.md`, `spec/actividades.md`) y los reportes de validación (`spec/<modulo>.validacion.md`).
