# Guía de pruebas manuales — Módulo `auth`

Prueba end-to-end del login, guard, gating por rol y refresh contra el backend real.

## Prerrequisitos
1. **Backend arriba** (lo corre el usuario): en `renaes-api`, `python manage.py runserver`
   → `http://localhost:8000`. API base `http://localhost:8000/api/v1/`.
2. **Usuario de prueba** con contraseña y al menos un perfil institucional (los superusuarios pasan
   sin perfil). Crear vía `python manage.py createsuperuser` o admin de Django si no existe.
3. **Frontend:** copiar `.env.example` → `.env.local` (ajustar `NEXT_PUBLIC_API_BASE_URL` si el
   backend no está en `localhost:8000`). Levantar con `npm run dev` (lo corre el usuario) →
   `http://localhost:3000`.

## 1. Login exitoso
1. Abrir `http://localhost:3000` sin sesión → debe **redirigir a `/login`**.
2. Ingresar usuario/contraseña válidos → "Ingresar".
3. Esperado: redirige a `/` (home protegida) y muestra **nombre, roles (`grupos`) y perfiles** del
   usuario (datos reales de `GET /auth/me/`).
4. Verificar en DevTools → Application → Local Storage → `renads-auth` contiene `accessToken` y `refreshToken`.

## 2. Credenciales inválidas
1. En `/login`, usar contraseña incorrecta → "Ingresar".
2. Esperado: toast "Credenciales inválidas…" (HTTP `401` de `/auth/token/`); permanece en `/login`.

## 3. Validación de formulario
1. Enviar con campos vacíos.
2. Esperado: mensajes "El usuario es obligatorio." / "La contraseña es obligatoria." (zod); no se llama al backend.

## 4. Guard de rutas
1. Con sesión activa, navegar a `/` → entra al shell.
2. Borrar `renads-auth` de Local Storage y recargar → **redirige a `/login`**.
3. Con sesión, entrar manualmente a `/login` → **redirige a `/`** (no muestra login con sesión).

## 5. Gating por rol
1. Iniciar sesión con un usuario de rol acotado (p. ej. solo `Universidad`).
2. Esperado en la navegación lateral: visibles **Inicio**, **Internados**, **Actividades**; **Convenios oculto**
   (requiere `Administrador RENADS`/`DIGEP`/`CONAPRES`/`OGAJ`/`Secretaría General`).
3. Con `Administrador RENADS` o superusuario: se ven **todos** los ítems.

## 6. Refresh automático (expiración de access)
1. Para forzarlo rápido, reducir `JWT_ACCESS_MINUTES` en el backend (`.env`) a 1 y reiniciar; iniciar sesión.
2. Esperar > 1 min y navegar/recargar para disparar una petición (`/auth/me/`).
3. Esperado: el interceptor llama `/auth/token/refresh/` de forma transparente, renueva el `access`
   (se actualiza en Local Storage) y la sesión continúa **sin volver a `/login`**.
4. Restaurar `JWT_ACCESS_MINUTES` tras la prueba.

## 7. Refresh fallido / logout
1. **Logout:** menú de usuario (arriba a la derecha) → "Cerrar sesión" → vuelve a `/login`; Local
   Storage limpio.
2. **Refresh inválido:** con sesión, alterar manualmente `refreshToken` en Local Storage a un valor
   inválido y forzar expiración del access (paso 6) → al fallar el refresh, la sesión se limpia y
   **redirige a `/login`**.

## Roles relevantes (referencia)
`Administrador RENADS`, `DIGEP`, `CONAPRES`, `OGAJ`, `Secretaría General`, `Universidad`, `Tutor`,
`Sede docente`, `Autoridad de convenio` (ver `docs/backend-overview.md`). El gating del front es UX;
la autorización real la impone el backend.
