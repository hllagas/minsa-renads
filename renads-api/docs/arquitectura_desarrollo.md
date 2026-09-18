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

### Runtime (instalado)
| Paquete | Versión | Rol |
|---------|---------|-----|
| Django | 6.0.6 | Framework base, ORM, migraciones |
| djangorestframework | 3.17.1 | Capa API REST |
| psycopg2-binary | 2.9.12 | Driver PostgreSQL |
| python-decouple | 3.8 | Configuración por entorno (`.env`) |
| dj-database-url | 3.1.2 | Parseo de `DATABASE_URL` (config 12-factor) |

### Infraestructura de desarrollo (Docker)
| Componente | Versión | Rol |
|------------|---------|-----|
| Docker Desktop | 29.8.0+ | Motor de contenedores (requiere WSL2 en Windows) |
| `python:3.14-slim-bookworm` | 3.14 | Imagen base del contenedor Django |
| PostgreSQL | 17-alpine | Base de datos en contenedor (`db`) |
| LibreOffice headless | sistema | Conversión DOCX → PDF (`soffice --convert-to pdf`) dentro del contenedor |

### A agregar (runtime)
| Paquete | Rol |
|---------|-----|
| `djangorestframework-simplejwt` | Autenticación JWT (access/refresh) |
| `drf-spectacular` | Documentación OpenAPI 3 (Swagger / Redoc) |
| `django-filter` | Filtrado declarativo de querysets |

### A agregar (desarrollo)
| Paquete | Rol |
|---------|-----|
| `ruff` | Linter + formateador |
| `mypy` + `django-stubs` | Tipado estático (se integra con la skill `/fix-types`) |
| `pytest` + `pytest-django` | Framework de pruebas |
| `factory_boy` | Factories para datos de prueba |

> **Base de datos:** PostgreSQL 17 tanto en desarrollo (Docker) como en producción. El entorno de desarrollo local sin Docker usa SQLite (`config/settings/dev.py`).

---

## 3. Estructura de carpetas

```
renads-api/
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py        # configuración común
│   │   ├── dev.py         # desarrollo local (SQLite, DEBUG=True)
│   │   ├── docker.py      # desarrollo Docker (PostgreSQL local, DEBUG=True)
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
├── Dockerfile            # imagen Python 3.14 + LibreOffice + dependencias del sistema
├── docker-compose.yml    # servicios: web (Django) + db (PostgreSQL 17)
├── .dockerignore
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
- **Selector:** encapsula lecturas reutilizables con alcance/filtros. Ejemplo: `listar_estudiantes_por_universidad(usuario)`.

---

## 5. Configuración por entorno

Settings en paquete `config/settings/` — `DJANGO_SETTINGS_MODULE` selecciona el entorno:

| Módulo | Cuándo usar | Base de datos |
|--------|-------------|---------------|
| `config.settings.dev` | desarrollo local sin Docker | SQLite (`db.sqlite3`) |
| `config.settings.docker` | desarrollo con Docker Compose | PostgreSQL 17 (contenedor `db`) |
| `config.settings.prod` | producción (Railway / VPS) | PostgreSQL (via `DATABASE_URL`) |

- Todo secreto/parámetro sensible vía `.env` con `python-decouple`:
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - `DATABASE_URL` (vía `dj-database-url`)
  - `JWT_*` (tiempos de vida de tokens)
  - credenciales de Cloudflare R2 / GCS (almacenamiento de objetos)
- `.env.example` versionado (sin secretos) como plantilla.

En Docker, `docker-compose.yml` inyecta directamente:
```yaml
environment:
  DJANGO_SETTINGS_MODULE: config.settings.docker
  DATABASE_URL: postgresql://renads:renads@db:5432/renads
```

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
  - **`id_objeto` como texto:** el `id_objeto` del `GenericForeignKey` de `perfil_usuario_entidad` (y de `bitacora_auditoria`) es `varchar(64)`, no entero. Para `Ipress` almacena el código RENIPRESS (PK textual de 8 chars); para las demás entidades, el pk entero casteado a `str`. **Todas las comparaciones de alcance se normalizan a `str`** en la fuente única `apps/common/selectors.py` (`entidades_del_usuario` devuelve `list[tuple[int, str]]`; `usuario_pertenece_a_entidad(..., id_objeto: str)` filtra por `str(id_objeto)`), en los permisos de objeto (`apps/internados/permissions.py`, `apps/actividades/permissions.py` envuelven cada lado de la tupla en `str(...)`), en las views (`apps/actividades/views.py` usa `str(ipress.pk)`) y en los serializers (`UserEntityProfileSerializer.id_objeto` y `UserEntityProfileWriteSerializer.ids` son `CharField`). En los selectores que filtran contra columnas enteras (universidad/estudiante) se castea de vuelta a `int`; contra `ipress_id` (texto) se mantiene `str`.

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
  - `/api/v1/internados/students/`, `/api/v1/internados/rotaciones/`
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
| Estudiante sobre Convenio Específico vigente | internados | `internados.services.crear_internado` |
| Duración internado ≤ 1 año | internados | `internados.services.crear_internado` |
| Rotación mismo ámbito geográfico sanitario | internados | `internados.services.crear_rotacion` |
| Máximo 4 rotaciones por estudiante | internados | `internados.services.crear_rotacion` |
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

## 11. Entorno de desarrollo con Docker

### Requisitos previos
- Docker Desktop 29.8.0+ con **WSL2** habilitado (Windows) o Docker Engine (Linux/macOS).
- Puerto `8000` (Django) y `5432` (PostgreSQL) libres en el host.

### Servicios declarados en `docker-compose.yml`

| Servicio | Imagen | Puerto host | Descripción |
|----------|--------|-------------|-------------|
| `db` | `postgres:17-alpine` | `5432` | PostgreSQL con healthcheck; credenciales `renads/renads/renads` |
| `web` | `renads-api-web` (build local) | `8000` | Django + runserver; espera a que `db` esté healthy |

El servicio `web` ejecuta al arrancar:
```sh
python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000
```

### Comandos habituales

```powershell
# Levantar (primera vez: construye la imagen)
docker compose up -d --build

# Levantar (sin rebuild)
docker compose up -d

# Ver logs del API
docker compose logs -f web

# Detener (conserva la BD)
docker compose down

# Detener y borrar la BD (BD limpia)
docker compose down -v

# Crear superusuario
docker compose exec web python manage.py createsuperuser

# Shell Django
docker compose exec web python manage.py shell

# Ejecutar migraciones manualmente
docker compose exec web python manage.py migrate
```

### Conexión a la base de datos (cliente externo)

```
Host:     localhost    Puerto: 5432
Database: renads       User:    renads    Password: renads
```

### Notas de la imagen Docker

- **LibreOffice headless** incluido para la generación de PDF desde plantillas DOCX (`soffice --convert-to pdf`).
- El directorio del proyecto se monta como volumen (`- .:/app`), por lo que los cambios de código se reflejan sin rebuild.
- Variables de entorno del `.env` se pasan al contenedor vía `env_file`; `DJANGO_SETTINGS_MODULE` y `DATABASE_URL` se sobreescriben en `docker-compose.yml`.

---

## 12. Calidad y pruebas

- **Lint/format:** `ruff` (config en `pyproject.toml`).
- **Tipado:** `mypy` + `django-stubs`; resolver incidencias con la skill **`/fix-types`**.
- **Pruebas:** `pytest` + `pytest-django`; `factory_boy` para factories. Cobertura prioritaria: **services** (reglas de negocio) y **API** (permisos/serialización).
- **Seed de catálogos:** vía **data migrations** (patrón ya establecido en `convenios/migrations/0002_*` y `0003_*`); reproducible e idempotente.
- **Comandos:** en desarrollo local activar el venv (`.venv\Scripts\Activate.ps1`); en Docker usar `docker compose exec web <comando>`; nunca `runserver` automatizado (lo corre el usuario o Docker).

---

## 13. Convenciones de código

- **Comunicación/documentación:** español. **Código** (variables, funciones, clases, endpoints, ramas, commits): inglés.
- **Modelo de datos:** nombres de tablas, columnas y descripción de campos en **español** (`db_table`, nombres de campo, `help_text`).
- **Apps de módulo (carpetas):** español — `convenios`, `internados`, `actividades`.
- Docstrings en español. Mantener los `docs/db_schema_modulo_0X_*.md` sincronizados con los modelos.

---

## 14. Roadmap del MVP

1. **Base técnica:** dependencias nuevas, `config/settings/` por entorno, `.env`/`.env.example`, migrar `SECRET_KEY`, registrar DRF/JWT/spectacular en `INSTALLED_APPS`, configurar `DATABASE_URL` Postgres, montar `/api/v1/` y OpenAPI.
2. **Autenticación y usuarios:** JWT, grupos/roles, `perfil_usuario_entidad`, permisos de alcance institucional.
3. **Módulo `convenios` end-to-end:** serializers, services (flujo + RN), selectors, permisos, filtros, endpoints de acción de estado, pruebas.
4. **Módulo `internados`:** estudiantes, internados, rotaciones, autorizaciones (RN críticas), pruebas.
5. **Módulo `actividades`:** registro y validación de actividades, pruebas.
6. **Adjuntos:** integrar el repositorio externo real vía `DocumentStorage`.

**Diferido (post-MVP):** notificaciones/alertas, reportes y exportación PDF/Excel, analítica, integraciones externas (RENIEC/SUNEDU), firma digital.

---

## Apéndice — Decisiones por defecto (ajustables)

- **Auth = JWT** asumiendo cliente SPA/móvil. Si el consumo fuese server-side renderizado, se usaría `SessionAuthentication`.
- **Settings split** (`base/dev/prod`); alternativa más simple para equipos pequeños: un único `settings.py` con `decouple`.
- **Sin capa de repositorio** adicional: el ORM de Django + selectors cubren el acceso a datos del MVP.
