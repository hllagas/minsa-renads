# Documentación — RENADS Frontend

Este frontend (Next.js) consume el backend **RENADS API** (`D:\dev\renaes\renaes-api`, Django + DRF).
Esta carpeta contiene el contexto necesario para construir la app sin tener que leer el código del backend.

> **RENADS** — Registro Nacional de Articulación Docencia-Servicio en Salud (MINSA, Perú).
> Registra y da seguimiento a la articulación entre entidades del sector salud y universidades
> que desarrollan docencia-servicio en salud.

## Índice

| Documento | Contenido |
|-----------|-----------|
| [backend-overview.md](backend-overview.md) | Stack del backend, base URL, paginación, filtros, OpenAPI, módulos y roles |
| [api-auth.md](api-auth.md) | Autenticación JWT, endpoints `/auth/*`, forma de `me`, roles/grupos |
| [api-convenios.md](api-convenios.md) | Módulo 1 — Gestionar Convenios: recursos, flujo, campos |
| [api-internados.md](api-internados.md) | Módulo 2 — Registrar Internados: internos, tutores, rotaciones |
| [api-actividades.md](api-actividades.md) | Módulo 3 — Registrar Actividades docente-asistenciales |
| [frontend-conventions.md](frontend-conventions.md) | Reglas de idioma/código, metodología SDD, estructura propuesta del front |

## Fuentes de verdad

El backend es la fuente de verdad del contrato de datos. Si un documento aquí queda obsoleto,
consultar el esquema OpenAPI vivo del backend (`/api/v1/schema/`, Swagger en `/api/v1/docs/`)
y los `docs/db_schema_*.md` del repo `renaes-api`. Mantener estos `.md` sincronizados con el
backend cuando cambie un contrato.

## Metodología

El backend se desarrolla con **Spec Driven Development (SDD)**. El frontend adopta el mismo
enfoque por módulo: spec → implementación → validación. Ver [frontend-conventions.md](frontend-conventions.md).
