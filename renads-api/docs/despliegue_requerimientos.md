# Guía de despliegue y requerimientos — RENADS

Documento formal de requerimientos de hardware y software para la puesta en
producción del sistema **RENADS (Registro Nacional de Articulación
Docencia-Servicio en Salud)** del MINSA.

> **Alcance:** describe el stack real del backend (`renads-api`) y del frontend
> (`minionpe-frontend`), los requerimientos mínimos y recomendados, las
> dependencias de sistema obligatorias y la arquitectura de despliegue prevista.
> Debe mantenerse sincronizado con `requirements.txt`, `Dockerfile`,
> `docker-compose.yml` y `config/settings/`.

---

## 1. Descripción del stack

### 1.1 Backend — `renads-api`

| Elemento | Tecnología | Versión |
|----------|-----------|---------|
| Lenguaje | Python | 3.14 |
| Framework web | Django | 6.0.6 |
| API | Django REST Framework | 3.17.1 |
| Autenticación | djangorestframework-simplejwt (JWT) + pyotp (2FA TOTP) | 5.5.1 / 2.9.0 |
| Documentación API | drf-spectacular (OpenAPI) | 0.29.0 |
| Servidor de aplicación | Gunicorn (WSGI) | 26.0.0 |
| Estáticos | WhiteNoise | 6.12.0 |
| Base de datos | PostgreSQL | 17 (15/16 compatibles) |
| Driver BD | psycopg2-binary | 2.9.12 |

**Modelo de ejecución:** síncrono (WSGI). **No** usa Redis, Celery, ni Django
Channels — no hay caché externa ni workers de tareas en segundo plano. Toda
petición se procesa dentro del worker de Gunicorn.

### 1.2 Procesamiento documental (consumidor de recursos)

| Función | Librería / dependencia | Nota |
|---------|------------------------|------|
| Generación de proyecto de convenio (Word → PDF) | **docxtpl 0.20.2 + LibreOffice headless** | `soffice --convert-to pdf` — **dependencia de sistema crítica** |
| Ensamblado de expediente (merge PDFs) | pypdf 6.14.2 | |
| Carga masiva de estudiantes | openpyxl 3.1.5 | Excel `.xlsx` |
| Procesamiento de imágenes (logos) | Pillow 11.3.0 | requiere libjpeg, zlib |
| OCR de PDFs (opcional, best-effort) | google-cloud-documentai 3.6.0 | `DOCAI_ENABLED=False` por defecto |

> **LibreOffice** es el mayor consumidor puntual de RAM/CPU del sistema. Cada
> conversión levanta un proceso `soffice`. Sin él, los endpoints
> `generar-proyecto` y `generar-expediente` **fallan** (error en español si el
> binario no está presente).

### 1.3 Almacenamiento de objetos (externo, obligatorio en producción)

PDFs (`documento_adjunto`) e imágenes de logos (`ImageField`) se almacenan en un
bucket externo S3-compatible, **no en disco local**. Precedencia de selección:

1. **Cloudflare R2** (`R2_ENABLED=True`) — boto3, presigned URLs `s3v4`. Bucket `renads-media`.
2. **Google Cloud Storage** (`GCS_ENABLED=True`) — auth keyless (ADC + impersonación de SA).
3. Stub / `FileSystemStorage` — **solo desarrollo**, no apto para producción.

Lectura siempre vía presigned URL de corta duración (default 900 s).

### 1.4 Frontend — `minionpe-frontend`

| Elemento | Tecnología | Versión |
|----------|-----------|---------|
| Framework | React | 18.3 |
| Bundler | Vite | 5.4 |
| Lenguaje | TypeScript | 5.7 |
| Estilos | Tailwind CSS | 4.0 |
| Estado servidor | TanStack Query | 5.62 |
| Cliente HTTP | axios / openapi-fetch | 1.19 / 0.13 |
| Mapas | Leaflet / react-leaflet | 1.9 / 4.2 |
| Gráficos | Recharts | 2.15 |
| PWA | vite-plugin-pwa | 1.3 |

**Modelo de despliegue:** build estático (`npm run build` → carpeta `dist/`). En
runtime **no requiere servidor Node** — se sirve como archivos estáticos
(Nginx, CDN o similar). Node.js solo es necesario en tiempo de build.

---

## 2. Requerimientos de software

### 2.1 Servidor de aplicación (backend)

| Componente | Versión mínima | Obligatorio | Nota |
|------------|----------------|-------------|------|
| Sistema operativo | Linux (Debian 12 / Ubuntu 22.04 LTS) | Sí | Dockerfile base: `python:3.14-slim-bookworm` |
| Python | 3.14 | Sí | Fijado por Django 6.0 |
| LibreOffice (headless) | cualquier estable con `soffice` | **Sí** | Generación de PDFs de convenios |
| libpq / libpq-dev | — | Sí | psycopg2 |
| libjpeg-dev, zlib1g-dev | — | Sí | Pillow (logos) |
| Gunicorn | 26.0.0 | Sí | Incluido en `requirements.txt` |
| Nginx (reverse proxy) | estable | Recomendado | TLS + estáticos + proxy a Gunicorn |

### 2.2 Base de datos

| Componente | Versión | Nota |
|------------|---------|------|
| PostgreSQL | 17 (15/16 sirven) | |
| Extensión `unaccent` | — | **Obligatoria** — búsquedas sin acentos (migración `apps/common/0007_unaccent_extension`). Requiere que el rol de BD pueda crear la extensión, o crearla manualmente. |

### 2.3 Servicios externos

| Servicio | Obligatorio en prod | Uso |
|----------|---------------------|-----|
| Almacenamiento S3-compatible (Cloudflare R2 **o** GCS) | **Sí** | PDFs y logos |
| SMTP | **Sí** | Notificaciones de onboarding del interno (RN-22) |
| Certificado TLS / HTTPS | **Sí** | `SECURE_SSL_REDIRECT`, cookies seguras, JWT |
| Google Cloud Document AI | No (opcional) | OCR de PDFs (best-effort, off por defecto) |

### 2.4 Tiempo de build del frontend

| Componente | Versión mínima | Nota |
|------------|----------------|------|
| Node.js | 20 LTS+ | Solo build (`npm run build`), no runtime |
| npm / pnpm | acorde a Node | Instalación de dependencias |

---

## 3. Requerimientos de hardware

### 3.1 Mínimo — piloto / baja concurrencia

Escenario: despliegue de validación o pocos usuarios concurrentes. App y BD
pueden compartir host.

| Recurso | Mínimo | Razón |
|---------|--------|-------|
| vCPU | **2** | 2–3 workers Gunicorn + proceso `soffice` |
| RAM | **4 GB** | ~300 MB por worker Django + **500 MB–1 GB por conversión LibreOffice** |
| Disco | **20 GB** SSD | SO + dependencias (LibreOffice ~500 MB) + logs. Media va a R2/GCS |
| PostgreSQL | 2 vCPU / 2–4 GB / 20 GB SSD | Puede compartir host en piloto |

### 3.2 Recomendado — producción MINSA (uso nacional)

| Recurso | Recomendado | Nota |
|---------|-------------|------|
| App server | **4 vCPU / 8 GB RAM** | Gunicorn `workers = (2 × núcleos) + 1` |
| Disco app | 40 GB SSD | Holgura para logs y binarios |
| PostgreSQL (dedicado) | **4 vCPU / 8 GB RAM / 100 GB SSD** | Con backups automáticos y punto de restauración |
| Frontend | Nginx / CDN estático | Recursos triviales; escala por CDN |
| Almacenamiento objetos | R2 / GCS gestionado | Crece con PDFs de convenios y DJ de internos |

### 3.3 Dimensionamiento por LibreOffice

La RAM debe dimensionarse **por picos, no por promedio**. Cada llamada a
`generar-expediente` / `generar-proyecto` levanta un `soffice` que consume
500 MB–1 GB. Conversiones concurrentes multiplican el consumo. Recomendación:

- Limitar la concurrencia de conversiones a nivel de aplicación, **o**
- Reservar RAM adicional proporcional al pico esperado de conversiones simultáneas.

---

## 4. Arquitectura de despliegue prevista

```
                    ┌─────────────────────────────┐
   Navegador  ───►  │  CDN / Nginx (frontend)     │   dist/ estático (React build)
                    └─────────────────────────────┘
                                 │  /api/*
                                 ▼
                    ┌─────────────────────────────┐
                    │  Nginx (reverse proxy, TLS) │
                    └─────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────┐
                    │  Gunicorn (WSGI) + Django   │  ── soffice (LibreOffice)
                    │  config.settings.prod       │
                    └─────────────────────────────┘
                         │                  │
                         ▼                  ▼
              ┌──────────────────┐   ┌──────────────────────┐
              │  PostgreSQL 17   │   │  Cloudflare R2 / GCS  │  PDFs + logos
              │  (+ unaccent)    │   │  (presigned URLs)     │
              └──────────────────┘   └──────────────────────┘
                                                 │
                                                 ▼
                                          ┌────────────┐
                                          │   SMTP     │  notificaciones
                                          └────────────┘
```

El repositorio incluye `Dockerfile` (instala LibreOffice + libs de sistema) y
`docker-compose.yml` (Postgres 17 + web) para despliegue contenedorizado. La
configuración de producción vive en `config/settings/prod.py`
(`DJANGO_SETTINGS_MODULE=config.settings.prod`).

---

## 5. Variables de entorno mínimas (producción)

Ver `.env.example` para el catálogo completo. Imprescindibles:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Django (no versionar) |
| `DEBUG=False` | Siempre desactivado en prod |
| `ALLOWED_HOSTS` | Dominios del backend |
| `DATABASE_URL` | Cadena de conexión PostgreSQL (con `sslmode`) |
| `CSRF_TRUSTED_ORIGINS` | Dominios del servicio |
| `CORS_ALLOWED_ORIGINS` | Dominio del frontend |
| `SECURE_SSL_REDIRECT=True` | Redirección HTTPS |
| `R2_*` **o** `GCS_*` | Almacenamiento de objetos (uno de los dos) |
| `EMAIL_*` | Credenciales SMTP |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | Vigencia de tokens |

---

## 6. Riesgos y consideraciones de escalado

1. **LibreOffice = pico de RAM.** Dimensionar por conversiones concurrentes; considerar cola/límite si el volumen crece.
2. **Stack síncrono sin caché ni workers.** Reportes/exportaciones pesadas bloquean el worker de Gunicorn. Si el sistema escala, evaluar **Redis + Celery** (no existen hoy) para tareas en segundo plano y caché.
3. **Media externa obligatoria.** Sin R2/GCS configurado, el sistema cae al stub/`FileSystemStorage` — no apto para producción.
4. **Extensión `unaccent`.** El rol de BD debe poder crearla, o crearla manualmente antes de migrar.
5. **Backups.** PostgreSQL y el bucket de objetos deben tener respaldo y plan de restauración (RNF-AUD, trazabilidad).

---

## 7. Checklist de puesta en producción

- [ ] Servidor Linux con Python 3.14 y LibreOffice headless instalados
- [ ] PostgreSQL 17 con extensión `unaccent` habilitada
- [ ] Bucket R2 o GCS creado y credenciales configuradas
- [ ] SMTP configurado y probado
- [ ] Certificado TLS/HTTPS activo (reverse proxy)
- [ ] Variables de entorno de `config.settings.prod` completas
- [ ] `python manage.py migrate` ejecutado
- [ ] `python manage.py collectstatic` ejecutado (WhiteNoise)
- [ ] Gunicorn tras Nginx con `workers = (2 × núcleos) + 1`
- [ ] Frontend construido (`npm run build`) y servido como estático/CDN
- [ ] Backups de BD y bucket configurados
```

