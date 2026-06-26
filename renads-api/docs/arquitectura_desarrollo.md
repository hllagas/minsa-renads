# Arquitectura de Desarrollo — RENADS API (MVP)

Documento de arquitectura para la implementación del API REST de RENADS. Define stack, estructura, capas, convenciones y hoja de ruta del MVP, alineado a buenas prácticas de Django/DRF y al schema de base de datos ya definido (ver [db_schema_er_global.md](db_schema_er_global.md) y los schemas por módulo).

---

## 1. Visión y principios

- **MVP enfocado:** registrar y dar seguimiento a Convenios, Internados y Actividades. Diferir notificaciones, reportería avanzada y analítica.
- **Separación por módulos:** tres apps Django independientes (`convenios`, `internados`, `actividades`) que reflejan los tres módulos funcionales.
- **Trazabilidad y auditoría como requisito transversal** (RNF-AUD): todo cambio de estado y operación crítica deja rastro (`bitacora_auditoria` + tablas de historial de estado).
- **Reglas de negocio explícitas y centralizadas:** las validaciones (convenio vigente, mismo ámbito sanitario, máximo de rotaciones, etc.) viven en una capa de servicios, no dispersas en vistas o modelos.
- **Seguridad por rol y ámbito institucional:** un usuario solo ve y opera sobre lo que le corresponde según su entidad (`perfil_usuario_entidad`).

---

## 2. Stack tecnológico

### Runtime (ya instalado)
| Paquete | Versión | Rol |
|---------|---------|-----|
| Django | 6.0.6 | Framework base, ORM, migraciones |
| djangorestframework | 3.17.1 | Capa API REST |
| psycopg2-binary | 2.9.12 | Driver PostgreSQL (producción) |
| python-decouple | 3.8 | Configuración por entorno (`.env`) |

### A agregar (runtime)
| Paquete | Rol |
|---------|-----|
| `djangorestframework-simplejwt` | Autenticación JWT (access/refresh) |
| `drf-spectacular` | Documentación OpenAPI 3 (Swagger / Redoc) |
| `django-filter` | Filtrado declarativo de querysets |
| `dj-database-url` | Parseo de `DATABASE_URL` (config 12-factor) |

### A agregar (desarrollo)
| Paquete | Rol |
|---------|-----|
| `ruff` | Linter + formateador |
| `mypy` + `django-stubs` | Tipado estático (se integra con la skill `/fix-types`) |
| `pytest` + `pytest-django` | Framework de pruebas |
| `factory_boy` | Factories para datos de prueba |

> **Base de datos:** SQLite en desarrollo, **PostgreSQL** en producción. El schema es agnóstico (sin tipos específicos de motor).

---

## 3. Estructura de carpetas

```
renads-api/
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py        # configuración común
│   │   ├── dev.py         # desarrollo (SQLite, DEBUG=True)
│   │   └── prod.py        # producción (PostgreSQL, DEBUG=False)
│   ├── urls.py            # URLconf raíz → incluye api/v1
│   ├── api_urls.py        # router de /api/v1/
│   ├── wsgi.py / asgi.py
├── apps/                 # contenedor de las apps de módulo
│   ├── __init__.py
│   ├── convenios/        # Módulo 1
│   ├── internados/       # Módulo 2
│   ├── actividades/      # Módulo 3
│   └── common/           # utilidades compartidas (storage, permisos base, auditoría, paginación)
├── docs/
├── manage.py
└── .env                  # NO versionado
```

> Las apps de módulo viven dentro de `apps/`. En `INSTALLED_APPS` se registran como `apps.convenios`, `apps.internados`, `apps.actividades`; cada `AppConfig` fija `label` (`convenios`, etc.) para mantener estable el `app_label` de migraciones y `content_type`. Imports cruzados: `from apps.convenios.models import ...`.

### Patrón por app (Django Styleguide — HackSoft)

```
<app>/
├── models.py        # modelos (ya existe)
├── serializers.py   # serializers DRF (read/write separados donde aplique)
├── services.py      # casos de uso de ESCRITURA + reglas de negocio (RN)
├── selectors.py     # consultas de LECTURA (filtros, agregados)
├── views.py         # ViewSets delgados: orquestan serializer + service/selector
├── permissions.py   # permisos por rol + alcance institucional
├── filters.py       # FilterSets de django-filter
├── urls.py          # router del módulo
├── admin.py
└── tests/
    ├── test_services.py
    ├── test_selectors.py
    └── test_api.py
```

**Regla de oro:** las vistas no contienen lógica de negocio. Validan entrada (serializer), delegan a un *service* (escritura) o *selector* (lectura) y serializan la salida.

---

## 4. Capas y flujo de request

```
Cliente (SPA/móvil)
   │  HTTP + JWT
   ▼
Router (/api/v1/...)
   ▼
ViewSet (DRF)               ← permisos (rol + ámbito institucional)
   ▼
Serializer (validación de forma)
   ▼
┌─────────────┬──────────────┐
│  Service    │   Selector   │
│ (escritura) │  (lectura)   │
│ + reglas RN │  + filtros   │
└─────────────┴──────────────┘
   ▼
ORM Django  →  PostgreSQL / SQLite
   │
   └─► bitacora_auditoria + historial_estado_* (efecto de los services)
```

- **Service:** recibe datos ya validados de forma, aplica **reglas de negocio**, persiste en transacción, registra auditoría y cambia estado/historial. Ejemplo: `crear_rotacion(internado, datos, usuario)`.
- **Selector:** encapsula lecturas reutilizables con alcance/filtros. Ejemplo: `listar_internos_por_universidad(usuario)`.

---

## 5. Configuración por entorno

- Settings en paquete `config/settings/` (`base`, `dev`, `prod`). `DJANGO_SETTINGS_MODULE` selecciona el entorno.
- Todo secreto/parámetro sensible vía `.env` con `python-decouple`:
  - `SECRET_KEY` (migrar — hoy hardcodeado), `DEBUG`, `ALLOWED_HOSTS`
  - `DATABASE_URL` (vía `dj-database-url`)
  - `JWT_*` (tiempos de vida de tokens)
  - credenciales del repositorio externo de archivos
- Proveer `.env.example` versionado (sin secretos) como plantilla.

```python
# config/settings/base.py (extracto)
from decouple import config
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
```

---

## 6. Autenticación y autorización

- **Autenticación:** JWT con `simplejwt`. Endpoints `/api/v1/auth/token/` (obtener) y `/api/v1/auth/token/refresh/`.
- **Roles:** `auth.Group` (Administrador RENADS, DIGEP, CONAPRES, OGAJ, Secretaría General, Universidad, Sede docente, Auditor…). Permisos de modelo vía `auth.Permission`.
- **Alcance institucional:** `perfil_usuario_entidad` vincula usuario ↔ entidad (polimórfica) ↔ rol. Las consultas se filtran por la entidad del usuario.

```python
# apps/common/permissions.py (ejemplo)
class HasInstitutionalScope(BasePermission):
    """El usuario solo accede a objetos dentro del ámbito de su entidad."""
    def has_object_permission(self, request, view, obj):
        return view.get_selector().pertenece_al_ambito(request.user, obj)
```

Baseline: `IsAuthenticated` + `DjangoModelPermissions` + permiso de alcance por objeto.

---

## 7. Diseño de API

- **Versionado:** prefijo `/api/v1/`. Routers DRF por app.
- **Recursos (ejemplos):**
  - `/api/v1/convenios/convenios/`, `/api/v1/convenios/campos-clinicos/`
  - `/api/v1/internados/internos/`, `/api/v1/internados/rotaciones/`
  - `/api/v1/actividades/actividades/`
- **Serializers:** `ModelSerializer`; separar lectura/escritura cuando difieran (p. ej. `ConvenioReadSerializer` / `ConvenioWriteSerializer`).
- **Acciones de flujo:** endpoints de acción para transiciones de estado (p. ej. `POST /convenios/{id}/validar-tecnica/`, `POST /rotaciones/{id}/autorizar/`), que invocan un service.
- **Paginación:** `PageNumberPagination` global. **Filtros/orden:** `django-filter` + `OrderingFilter`.
- **Errores:** exception handler personalizado con formato consistente:

```json
{ "error": { "codigo": "REGLA_NEGOCIO", "mensaje": "...", "detalles": {} } }
```

- **Documentación:** `drf-spectacular` → esquema en `/api/schema/`, Swagger en `/api/docs/`, Redoc en `/api/redoc/`.

---

## 8. Reglas de negocio → service responsable

| Regla | Módulo | Service |
|-------|--------|---------|
| Específico requiere Marco vigente (RN-3, M1) | convenios | `convenios.services.crear_convenio` |
| No firmar con observaciones pendientes | convenios | `convenios.services.registrar_firma` |
| Interno sobre Convenio Específico vigente | internados | `internados.services.crear_internado` |
| Duración internado ≤ 1 año | internados | `internados.services.crear_internado` |
| Rotación mismo ámbito geográfico sanitario | internados | `internados.services.crear_rotacion` |
| Máximo 4 rotaciones por interno | internados | `internados.services.crear_rotacion` |
| Rotación no inicia sin autorización | internados | `internados.services.autorizar_rotacion` / `iniciar_rotacion` |
| No exceder campos clínicos autorizados | internados | `internados.services.crear_internado` |
| Cambio de tutor con fecha/motivo/responsable | internados | `internados.services.cambiar_tutor` |
| Actividad solo sobre internado activo + periodo | actividades | `actividades.services.registrar_actividad` |
| Actividad en rotación → rotación autorizada | actividades | `actividades.services.registrar_actividad` |
| Validadas no se modifican sin trazabilidad | actividades | `actividades.services.validar_actividad` |

---

## 9. Adjuntos en repositorio externo

- El binario **no** se guarda en la BD ni en el filesystem de la app; vive en un repositorio externo (S3/MinIO u otro), configurable después.
- El modelo `Document` (`documento`) guarda solo `referencia_externa` (clave/URL), `nombre_archivo`, `version`, `estado` y `version_anterior` (versionado).
- Abstracción en `apps/common/storage.py`:

```python
class DocumentStorage(Protocol):
    def subir(self, archivo, ruta: str) -> str: ...   # devuelve referencia_externa
    def url_firmada(self, referencia: str) -> str: ...
    def eliminar(self, referencia: str) -> None: ...
```

- Service `apps.common.services.adjuntar_documento(objeto, archivo, tipo, usuario)` sube al storage, crea el `Document` (relación genérica) y, si reemplaza, enlaza `version_anterior` y marca la previa como `REEMPLAZADO`.

---

## 10. Auditoría y trazabilidad

- **Bitácora (`bitacora_auditoria`):** se escribe **explícitamente desde los services** en operaciones críticas (crear/actualizar/eliminar/cambio de estado), registrando usuario, acción, entidad afectada, valor anterior/nuevo. Se evita el uso de signals para mantener el flujo explícito y testeable.
- **Historiales de estado:** `historial_estado_convenio`, `historial_estado_internado`, `historial_estado_rotacion`, `historial_estado_actividad` registran cada transición. Helper común `registrar_cambio_estado(objeto, estado, usuario, observacion)`.
- Toda escritura de negocio ocurre dentro de `transaction.atomic()` para garantizar consistencia entre el cambio, su historial y la bitácora.

---

## 11. Calidad y pruebas

- **Lint/format:** `ruff` (config en `pyproject.toml`).
- **Tipado:** `mypy` + `django-stubs`; resolver incidencias con la skill **`/fix-types`**.
- **Pruebas:** `pytest` + `pytest-django`; `factory_boy` para factories. Cobertura prioritaria: **services** (reglas de negocio) y **API** (permisos/serialización).
- **Seed de catálogos:** vía **data migrations** (patrón ya establecido en `convenios/migrations/0002_*` y `0003_*`); reproducible e idempotente.
- **Comandos:** ejecutar siempre con el venv activado (`.venv\Scripts\Activate.ps1`); nunca `runserver` automatizado (lo corre el usuario).

---

## 12. Convenciones de código

- **Comunicación/documentación:** español. **Código** (variables, funciones, clases, endpoints, ramas, commits): inglés.
- **Modelo de datos:** nombres de tablas, columnas y descripción de campos en **español** (`db_table`, nombres de campo, `help_text`).
- **Apps de módulo (carpetas):** español — `convenios`, `internados`, `actividades`.
- Docstrings en español. Mantener los `docs/db_schema_modulo_0X_*.md` sincronizados con los modelos.

---

## 13. Roadmap del MVP

1. **Base técnica:** dependencias nuevas, `config/settings/` por entorno, `.env`/`.env.example`, migrar `SECRET_KEY`, registrar DRF/JWT/spectacular en `INSTALLED_APPS`, configurar `DATABASE_URL` Postgres, montar `/api/v1/` y OpenAPI.
2. **Autenticación y usuarios:** JWT, grupos/roles, `perfil_usuario_entidad`, permisos de alcance institucional.
3. **Módulo `convenios` end-to-end:** serializers, services (flujo + RN), selectors, permisos, filtros, endpoints de acción de estado, pruebas.
4. **Módulo `internados`:** internos, internados, rotaciones, autorizaciones (RN críticas), pruebas.
5. **Módulo `actividades`:** registro y validación de actividades, pruebas.
6. **Adjuntos:** integrar el repositorio externo real vía `DocumentStorage`.

**Diferido (post-MVP):** notificaciones/alertas, reportes y exportación PDF/Excel, analítica, integraciones externas (RENIEC/SUNEDU), firma digital.

---

## Apéndice — Decisiones por defecto (ajustables)

- **Auth = JWT** asumiendo cliente SPA/móvil. Si el consumo fuese server-side renderizado, se usaría `SessionAuthentication`.
- **Settings split** (`base/dev/prod`); alternativa más simple para equipos pequeños: un único `settings.py` con `decouple`.
- **Sin capa de repositorio** adicional: el ORM de Django + selectors cubren el acceso a datos del MVP.
