# Guía de pruebas manuales — Módulo `internados`

Cómo probar manualmente los endpoints del módulo. Generada por el agente **validator** tras validación exitosa.

## Prerrequisitos

1. Servidor: `python manage.py runserver` (lo corre el usuario). Base: `http://localhost:8000/api/v1/`. Swagger: `/api/v1/docs/`.
2. **Token JWT:** `POST /api/v1/auth/token/` → usar `Authorization: Bearer <access>`.
3. **Roles usados:** `Universidad` (registrar internos/tutores/internados/rotaciones, iniciar rotación), `Autoridad de convenio` (autorizar rotación), `Administrador RENADS` (transiciones de estado). Atajo camino feliz: superusuario.
4. **Datos del módulo 1 ya existentes** (crear con la guía de `convenios` o seed): un **Convenio Específico VIGENTE**, un **campo clínico** asociado, e **IPRESS** del mismo ámbito geográfico sanitario. Catálogos seedeados: `internship-statuses` (12), `rotation-statuses` (8), `identity-document-types` (`DNI`/`CE`/`PASAPORTE`); crear `service-areas` si hace falta.

## Flujo paso a paso

1. **Registrar interno** (rol `Universidad`; la universidad debe estar en tu ámbito):
   ```
   POST /api/v1/interns/
   { "tipo_documento_identidad": <id DNI>, "numero_documento": "70011223",
     "nombres": "Ana", "apellido_paterno": "López", "universidad": <UNI>,
     "carrera_profesional": <id> }
   → 201  (creado_por se asigna solo)   (guardar id = INTERNO)
   ```
2. **Registrar tutor** (rol `Universidad`):
   ```
   POST /api/v1/tutors/
   { "tipo_documento_identidad": <id DNI>, "numero_documento": "10203040",
     "nombres": "Carlos", "apellido_paterno": "Ríos" }
   → 201   (guardar id = TUTOR)
   ```
3. **Crear internado** (rol `Universidad`):
   ```
   POST /api/v1/internships/
   { "interno": INTERNO, "convenio": <ESP vigente>, "campo_clinico": <id>,
     "ipress": <id IP1>, "tutor": TUTOR, "ambito_geografico_sanitario": <id>,
     "fecha_inicio": "2026-04-01", "fecha_fin": "2026-12-01" }
   → 201  estado_codigo="REGISTRADO"   (guardar id = INT)
   ```
4. **Activar internado** (rol `Administrador RENADS`):
   ```
   POST /api/v1/internships/{INT}/cambiar-estado/
   { "estado_codigo": "ACTIVO" }
   → 200  estado_codigo="ACTIVO"
   ```
5. **Solicitar rotación** (rol `Universidad`; ambas sedes del mismo ámbito que el internado):
   ```
   POST /api/v1/internships/{INT}/rotaciones/
   { "ipress_origen": <IP1>, "ipress_destino": <IP2>, "servicio_area": <id>,
     "fecha_inicio": "2026-05-01", "fecha_fin": "2026-06-01" }
   → 200 (lista de rotaciones; la nueva tiene numero_rotacion=1)   (guardar id = ROT)
   ```
6. **Autorizar rotación** (rol `Autoridad de convenio`; el participante debe ser firmante del Convenio Específico):
   ```
   POST /api/v1/rotations/{ROT}/autorizar/
   { "participante_convenio": <id participante firmante>, "resultado": "APROBADO",
     "fecha_autorizacion": "2026-04-20" }
   → 200  estado_codigo="AUTORIZADA"
   ```
7. **Iniciar rotación** (rol `Universidad`):
   ```
   POST /api/v1/rotations/{ROT}/iniciar/
   {}
   → 200  estado_codigo="EN_CURSO"
   ```
8. **Cambiar tutor** (rol `Universidad`, queda en historial — RN-14):
   ```
   POST /api/v1/internships/{INT}/cambiar-tutor/
   { "tutor": <id otro tutor>, "fecha_cambio": "2026-06-15", "motivo": "Rotación de docente" }
   → 200
   ```
9. **Consultar historiales:**
   ```
   GET /api/v1/internships/{INT}/historial/      → estados del internado
   GET /api/v1/rotations/{ROT}/historial/        → estados de la rotación
   ```

## Casos que deben fallar (reglas de negocio)

- **RN-6** — internado con `fecha_fin` a más de 1 año de `fecha_inicio` (paso 3) → `400`.
- **RN-13** — crear internado sobre un campo clínico que ya alcanzó su `cantidad_maxima` → `400`.
- **RN-2/3/4** — `convenio` que no es Específico o no está vigente (paso 3) → `400`.
- **RN-8** — rotación con `ipress_origen`/`ipress_destino` de un ámbito distinto al del internado (paso 5) → `400`.
- **RN-9** — solicitar una 5.ª rotación para el mismo interno → `400`.
- **RN-11** — `iniciar` una rotación sin autorización `APROBADO` (saltarse el paso 6) → `400`.
- **RN-10** — `autorizar` con un `participante_convenio` que no es firmante del Convenio Específico → `400`.
- **Cross-tenant** — usuario de la Universidad A registra un interno de la Universidad B → `403`.

## Roles por endpoint

| Endpoint | Rol requerido |
|----------|---------------|
| `POST interns/`, `tutors/` | Universidad o Administrador RENADS |
| `POST internships/`, `internships/{id}/rotaciones/`, `cambiar-tutor` | Universidad |
| `internships/{id}/cambiar-estado`, `rotations/{id}/cambiar-estado` | Administrador RENADS |
| `rotations/{id}/autorizar` | Autoridad de convenio |
| `rotations/{id}/iniciar` | Universidad |
| catálogos (GET) / lecturas | cualquier usuario autenticado (con alcance institucional) |
