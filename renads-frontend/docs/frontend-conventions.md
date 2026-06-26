# Convenciones del Frontend + Metodología SDD

## Idioma

Igual que el backend:

- **UI, textos, comentarios, docstrings y `.md`: español.**
- **Código (variables, funciones, componentes, rutas, ramas, commits): inglés.**
- Los **campos del API van en español** (`fecha_inicio`, `estado_codigo`). Mantenerlos tal cual al
  tipar las respuestas; no traducir claves del payload.

## Metodología — Spec Driven Development (SDD)

El backend se construye con SDD (spec → implement → validate). El frontend adopta el mismo flujo
por módulo/feature:

1. **Spec** — antes de codear, escribir la spec del feature en `spec/<feature>.md`
   (pantallas, datos consumidos, endpoints, estados, reglas de UX, criterios de aceptación).
2. **Implement** — desarrollar contra la spec; ViewModels/hooks de datos separados de la UI.
3. **Validate** — revisar contra la spec y el contrato del backend (campos, roles, estados).

No avanzar a UI sin contrato claro; no cerrar un feature sin validar contra el API real.

## Contrato del API

- Fuente de verdad: el backend. Preferir **generar tipos** desde OpenAPI
  (`/api/v1/schema/`) con `openapi-typescript` antes que escribir tipos a mano.
- Centralizar la base URL en `NEXT_PUBLIC_API_BASE_URL` (dev: `http://localhost:8000/api/v1`).
- Un cliente HTTP único que: inyecte `Authorization: Bearer`, maneje refresh en `401`,
  y normalice la forma paginada (`{ count, next, previous, results }`).

## Gating por rol / alcance

- Roles desde `me.grupos`; perfiles/entidades desde `me.perfiles` (ver [api-auth.md](api-auth.md)).
- Ocultar acciones que el backend rechazaría por rol (p. ej. botón "Firmar" solo a
  `Secretaría General`). El backend es la autoridad final; el gating del front es UX, no seguridad.
- Usar `estado_codigo` (no el nombre legible) para lógica de transiciones y condicionales.

## Estructura propuesta (App Router)

Por confirmar al implementar, alineada con los 3 módulos:

```
app/
  (auth)/login/
  convenios/        # módulo 1
  internados/       # módulo 2
  actividades/      # módulo 3
lib/
  api/              # cliente HTTP, tipos (generados de OpenAPI), endpoints por módulo
  auth/             # tokens, refresh, contexto de usuario (me)
spec/               # specs SDD por feature
```

> Mantener `docs/` sincronizada con el backend: si cambia un contrato (campos, endpoints, roles),
> actualizar el `.md` correspondiente en el mismo cambio.
