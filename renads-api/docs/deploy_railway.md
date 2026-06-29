# Despliegue en Railway — RENADS API

Guía para publicar el API (Django 6 + DRF) en [Railway](https://railway.app) con PostgreSQL.
El despliegue lo ejecuta el usuario; este documento es el checklist de configuración.

## 1. Resumen de la arquitectura de deploy

- **Build:** NIXPACKS (autodetecta Python por `.python-version` = 3.14 y `requirements.txt`).
- **Settings de producción:** `config/settings/prod.py` (PostgreSQL vía `DATABASE_URL`, WhiteNoise,
  hardening HTTPS, CORS/CSRF por variables). `config/wsgi.py` ya usa `config.settings.prod` por defecto.
- **Procfile:**
  - `release` → `migrate` + `collectstatic` (ambos con `--settings=config.settings.prod`).
  - `web` → `gunicorn config.wsgi`.
- **`railway.json`:** builder NIXPACKS, `startCommand` gunicorn ligado a `$PORT`, healthcheck en
  `/api/v1/docs/`, reinicio `ON_FAILURE`.

## 2. Crear el proyecto en Railway

1. Crear un proyecto y conectar el repositorio (deploy automático en cada `git push`).
   - **Root Directory:** si el repo contiene `renads-api/` como subcarpeta, fijar el root del servicio
     a `renads-api/` (donde están `manage.py`, `Procfile`, `railway.json`).
2. Añadir un plugin **PostgreSQL** al proyecto. Railway expone `DATABASE_URL` automáticamente;
   referenciarla en el servicio del API (`${{ Postgres.DATABASE_URL }}`).

## 3. Variables de entorno (servicio del API)

| Variable | Obligatoria | Ejemplo / nota |
|----------|-------------|----------------|
| `DJANGO_SETTINGS_MODULE` | Recomendada | `config.settings.prod` (refuerza prod en todos los comandos) |
| `SECRET_KEY` | **Sí** | cadena larga aleatoria; **no** reutilizar la de desarrollo |
| `DATABASE_URL` | **Sí** | `${{ Postgres.DATABASE_URL }}` (referencia al plugin Postgres) |
| `ALLOWED_HOSTS` | **Sí** | `renads-api.up.railway.app` (+ dominio propio, separado por comas) |
| `CSRF_TRUSTED_ORIGINS` | **Sí** | `https://renads-api.up.railway.app` (con esquema `https://`) |
| `CORS_ALLOWED_ORIGINS` | **Sí** (si hay frontend) | `https://<frontend>.vercel.app` (esquema + sin barra final) |
| `DEBUG` | No | omitir (prod fuerza `DEBUG=False`) |
| `SECURE_SSL_REDIRECT` | No | `True` por defecto; poner `False` solo si se depura sin TLS |
| `PAGE_SIZE` | No | `20` (default) |
| `JWT_ACCESS_MINUTES` | No | `60` (default) |
| `JWT_REFRESH_DAYS` | No | `1` (default) |

> `Csv()`: las variables multivalor (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`)
> se escriben separadas por comas, sin espacios: `a.com,b.com`.

## 4. Flujo de despliegue

1. Configurar todas las variables de la sección 3.
2. `git push` a la rama conectada → Railway ejecuta build (NIXPACKS) y luego el `release`
   (`migrate` + `collectstatic` contra Postgres) y arranca `web` (gunicorn).
3. Crear el superusuario una vez (terminal del servicio en Railway):
   `python manage.py createsuperuser --settings=config.settings.prod`.
   - Los catálogos y roles se siembran solos vía data migrations en `release`.

## 5. Verificación post-deploy

- `GET https://<dominio>/api/v1/docs/` → Swagger UI carga (healthcheck verde).
- `POST https://<dominio>/api/v1/auth/token/` con el superusuario → devuelve `access`/`refresh`.
- Con el token: `GET /api/v1/conventions/`, `GET /api/v1/documents/`, `GET /api/v1/audit-logs/`
  (este último requiere rol Administrador RENADS) responden `200`.
- `GET /api/v1/regions/` lista catálogos sembrados.

## 6. Notas

- **Almacenamiento de documentos:** el MVP usa referencia externa (stub, `apps/common/storage.py`).
  No hay disco persistente de archivos; integrar S3/MinIO antes de cargar binarios reales.
- **Disco efímero:** Railway reinicia con FS efímero; no depender del filesystem para datos
  (la BD es el plugin Postgres, no SQLite).
- **Estáticos:** los sirve WhiteNoise desde `staticfiles/` generado en `collectstatic`.
