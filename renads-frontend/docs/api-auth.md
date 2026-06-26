# API — Autenticación y usuario actual

Transversal (`apps/common`). Base: `/api/v1/`.

## Endpoints

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/auth/token/` | Obtiene par de tokens JWT (access + refresh) | No |
| POST | `/auth/token/refresh/` | Renueva el `access` a partir de un `refresh` | No |
| GET | `/auth/me/` | Identidad, roles y perfiles institucionales del usuario | Sí |

### POST `/auth/token/`

Request:
```json
{ "username": "usuario", "password": "secreto" }
```

Response:
```json
{ "access": "<jwt>", "refresh": "<jwt>" }
```

El `access` incluye claims extra: `nombre` (nombre completo o username) y `grupos` (lista de roles).
Vida del `access`: 60 min (config `JWT_ACCESS_MINUTES`). `refresh`: 1 día, con rotación
(`ROTATE_REFRESH_TOKENS = True`) — al refrescar se emite un nuevo `refresh`.

### POST `/auth/token/refresh/`

Request: `{ "refresh": "<jwt>" }` → Response: `{ "access": "<jwt>", "refresh": "<jwt>" }`.

### GET `/auth/me/`

Response:
```json
{
  "id": 1,
  "username": "jperez",
  "email": "jperez@minsa.gob.pe",
  "nombre": "Juan Pérez",
  "es_superusuario": false,
  "grupos": ["Universidad"],
  "perfiles": [
    {
      "tipo_entidad": "university",
      "id_objeto": 12,
      "entidad": "Universidad Nacional Mayor de San Marcos",
      "rol": "Universidad"
    }
  ]
}
```

- `grupos` → roles globales (gating de acciones en la UI).
- `perfiles` → vínculos del usuario con entidades concretas (alcance institucional).
  `tipo_entidad` es el modelo backend (`university`, `ipress`, `minsaorgan`, ...).

## Uso en el front

1. Login → guardar `access` + `refresh`.
2. Enviar `Authorization: Bearer <access>` en cada request.
3. Ante `401`, intentar `/auth/token/refresh/`; si falla, redirigir a login.
4. Cargar `/auth/me/` tras login para conocer `grupos` y `perfiles` (gating de menús/acciones).

> Expiración automática de sesión (RNF-SEG-07): respetar la vida del token; no extender sesión
> indefinidamente del lado del cliente.
