# Backend Overview — RENADS API

Repositorio: `D:\dev\renaes\renaes-api`

## Stack

- **Django 6 + Django REST Framework** (Python 3.14).
- **Auth:** `djangorestframework-simplejwt` (Bearer JWT).
- **OpenAPI:** `drf-spectacular`.
- **Filtros:** `django-filter` + `OrderingFilter` + `SearchFilter`.
- **BD:** SQLite en dev, PostgreSQL en prod.
- Arquitectura por capas (estilo HackSoft): ViewSets delgados → `services.py` (escritura, reglas de
  negocio, transacciones, auditoría) y `selectors.py` (lecturas con alcance institucional).

## Base URL

```
http://localhost:8000/api/v1/
```

Todas las rutas cuelgan de `/api/v1/`. El servidor de desarrollo lo levanta el usuario
(`python manage.py runserver`, puerto 8000 por defecto).

> **CORS / proxy:** el backend aún no declara dominios del front. Para desarrollo, usar un proxy
> de Next (`rewrites` o variable `NEXT_PUBLIC_API_BASE_URL`) y coordinar `ALLOWED_HOSTS` /
> `CSRF_TRUSTED_ORIGINS` cuando se despliegue.

## Convenciones del contrato

- **Endpoints en inglés** (kebab-case): `conventions`, `teaching-activities`, `clinical-fields`.
- **Campos del payload en español**: `titulo`, `fecha_inicio`, `estado_codigo`, `creado_por`.
- **Idioma de errores y `help_text`: español** (mostrables al usuario).
- Estados se exponen como par legible + código: `estado_actual` (nombre) y `estado_codigo`
  (código estable para lógica del front, p. ej. `VIGENTE`, `REGISTRADO`).

## Paginación

`PageNumberPagination`, `PAGE_SIZE = 20`. Las listas devuelven:

```json
{ "count": 0, "next": null, "previous": null, "results": [] }
```

Parámetros: `?page=N`. Filtros por campo (django-filter), `?ordering=campo` / `-campo`,
y `?search=texto` en los recursos con `search_fields`.

## Autenticación

JWT Bearer en cabecera `Authorization: Bearer <access>`. Permiso global por defecto
`IsAuthenticated` — **todos los endpoints requieren token** salvo la obtención del token.
La mayoría de recursos de negocio además exigen `IsInstitutionalMember` (el usuario debe tener
al menos un perfil institucional activo) y aplican **alcance institucional** por entidad.
Detalle en [api-auth.md](api-auth.md).

## Módulos

| # | Módulo | App backend | Doc |
|---|--------|-------------|-----|
| 1 | Gestionar Convenios | `apps/convenios` | [api-convenios.md](api-convenios.md) |
| 2 | Registrar Internados | `apps/internados` | [api-internados.md](api-internados.md) |
| 3 | Registrar Actividades | `apps/actividades` | [api-actividades.md](api-actividades.md) |

`apps/common` aporta lo transversal: login JWT con claims, endpoint `me`, permisos de alcance
institucional y auditoría.

## Roles / grupos (Django Groups)

El front debe ocultar/mostrar acciones según los grupos del usuario (vienen en el claim `grupos`
del token y en `me.grupos`):

- `Administrador RENADS` — transiciones administrativas, master-data, asignación de perfiles.
- `DIGEP` — evaluación técnica de convenios.
- `CONAPRES` — opinión CONAPRES y campos clínicos.
- `OGAJ` — opinión jurídica.
- `Secretaría General` — firma y publicación de convenios.
- `Universidad` — registrar internos/internados, rotaciones, cambio de tutor.
- `Tutor` — validar actividades.
- `Sede docente` — registrar actividades.
- `Autoridad de convenio` — autorizar rotaciones.

El alcance institucional restringe además **qué objetos** ve/edita cada usuario (su universidad,
IPRESS, etc.), no solo qué acciones. Superusuario y `Administrador RENADS` están exentos del
filtro de alcance.

## OpenAPI vivo

- Esquema: `GET /api/v1/schema/`
- Swagger UI: `/api/v1/docs/`
- ReDoc: `/api/v1/redoc/`

Útil para generar un cliente TypeScript tipado (p. ej. `openapi-typescript`) en lugar de tipos a mano.
