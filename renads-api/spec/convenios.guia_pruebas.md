# Guía de pruebas manuales — Módulo `convenios`

Cómo probar manualmente los endpoints del módulo. Generada por el agente **validator** tras validación exitosa.

## Prerrequisitos

1. Levantar el servidor (lo corre el usuario): `python manage.py runserver`.
2. URL base: `http://localhost:8000/api/v1/`. Documentación interactiva: `http://localhost:8000/api/v1/docs/` (Swagger).
3. **Token JWT:**
   ```
   POST /api/v1/auth/token/
   { "username": "<usuario>", "password": "<clave>" }
   → 200 { "access": "...", "refresh": "..." }
   ```
   En las siguientes llamadas usar header: `Authorization: Bearer <access>`.
4. **ContentType de `university`** (necesario para `solicitante_tipo_contenido`): no hay endpoint público; obtenerlo en `/admin/` (tabla `django_content_type`) o `manage.py shell` (`ContentType.objects.get_for_model(University).id`). En estos ejemplos se asume `CT_UNI`.
5. **Usuarios/roles:** crear usuarios con grupos (roles) y un `perfil_usuario_entidad` ligando al usuario con su entidad. Atajo para el camino feliz: usar un **superusuario** (omite restricciones de rol y ámbito). Roles usados: `DIGEP`, `CONAPRES`, `OGAJ`, `Secretaría General`, `Administrador RENADS`.

## Datos previos
- Catálogos ya seedeados: `convention-types` (`MARCO`, `ESPECIFICO`), `convention-statuses` (26), `specialties`, `regions`, etc. (GET `/api/v1/convention-types/` para ver ids).
- Crear una **universidad** solicitante (rol `Administrador RENADS`):
  ```
  POST /api/v1/universities/
  { "nombre": "UNMSM", "siglas": "UNMSM", "tipo_gestion": <id>, "tipo_entidad": <id>, "tipo_autorizacion": <id> }
  → 201  (guardar id = UNI)
  ```
  (ids de `tipo_gestion`/`tipo_entidad`/`tipo_autorizacion` vía GET a `/api/v1/university-management-types/`, etc.)

## Flujo paso a paso

1. **Crear Convenio Marco** (entidad solicitante dentro de tu ámbito):
   ```
   POST /api/v1/conventions/
   { "tipo_convenio": <id MARCO>, "titulo": "Convenio Marco UNMSM",
     "solicitante_tipo_contenido": CT_UNI, "solicitante_id_objeto": UNI,
     "fecha_solicitud": "2026-01-10", "fecha_inicio": "2026-02-01" }
   → 201  estado_codigo="SOLICITUD_REGISTRADA", fecha_fin="2030-02-01" (+4 años)   (guardar id = MARCO)
   ```
2. **Pasar el Marco a vigente** (rol `Administrador RENADS`):
   ```
   POST /api/v1/conventions/{MARCO}/cambiar-estado/
   { "estado_codigo": "VIGENTE" }
   → 200  estado_codigo="VIGENTE"
   ```
3. **Crear Convenio Específico** sobre el Marco vigente:
   ```
   POST /api/v1/conventions/
   { "tipo_convenio": <id ESPECIFICO>, "convenio_marco": MARCO, "titulo": "Específico Medicina",
     "solicitante_tipo_contenido": CT_UNI, "solicitante_id_objeto": UNI,
     "fecha_solicitud": "2026-03-01", "fecha_inicio": "2026-03-01", "max_campos_clinicos": 10 }
   → 201  fecha_fin="2029-03-01" (+3 años)   (guardar id = ESP)
   ```
4. **Evaluación técnica** (rol `DIGEP`):
   ```
   POST /api/v1/conventions/{ESP}/evaluacion-tecnica/
   { "resultado": "VALIDADO", "fecha_evaluacion": "2026-03-05" }
   → 200  estado_codigo="VALIDADO_TECNICAMENTE"
   ```
5. **Opinión CONAPRES** (rol `CONAPRES`, solo Específico):
   ```
   POST /api/v1/conventions/{ESP}/opinion-conapres/
   { "fecha_solicitud": "2026-03-06", "estado_atencion": "ATENDIDO", "resultado_opinion": "FAVORABLE" }
   → 200  estado_codigo="CONAPRES_FAVORABLE"
   ```
6. **Definir campo clínico** (rol `CONAPRES`):
   ```
   POST /api/v1/conventions/{ESP}/campos-clinicos/
   { "ipress": <id>, "carrera_profesional": <id>, "cantidad_maxima": 5,
     "vigencia_inicio": "2026-03-01", "vigencia_fin": "2029-03-01", "ambito_geografico_sanitario": <id> }
   → 200 (lista de campos clínicos)   estado del convenio → "CAMPOS_CLINICOS_DEFINIDOS"
   ```
7. **Opinión jurídica** (rol `OGAJ`):
   ```
   POST /api/v1/conventions/{ESP}/opinion-juridica/
   { "fecha_envio": "2026-03-10", "resultado_opinion": "FAVORABLE" }
   → 200  estado_codigo="OGAJ_FAVORABLE"
   ```
8. **Agregar participante firmante** (rol `Administrador RENADS`):
   ```
   POST /api/v1/conventions/{ESP}/participantes/
   { "tipo_contenido": CT_UNI, "id_objeto": UNI, "es_firmante": true }
   → 200 (lista de participantes)
   ```
9. **Registrar firma** (rol `Secretaría General`):
   ```
   POST /api/v1/conventions/{ESP}/firma/
   { "firmante_tipo_contenido": CT_UNI, "firmante_id_objeto": UNI, "estado_firma": "FIRMADO" }
   → 200  estado_codigo="FIRMADO_EXTERNOS"
   ```
10. **Publicar** (rol `Secretaría General`):
    ```
    POST /api/v1/conventions/{ESP}/publicacion/
    { "fecha_publicacion": "2026-03-20", "referencia_publicacion": "RES-001-2026" }
    → 200  estado_codigo="PUBLICADO"
    ```
11. **Consultar trazabilidad:**
    ```
    GET /api/v1/conventions/{ESP}/historial/
    → 200 (lista de cambios de estado con responsable y fecha)
    ```

## Casos que deben fallar (reglas de negocio)

- **RN-3** — Específico sin Marco vigente: repetir paso 3 con un `convenio_marco` cuyo estado **no** sea vigente → `400` (`"El Convenio Marco debe estar vigente."`).
- **RN-9 (firma)** — registrar una evaluación técnica `OBSERVADO` y luego intentar la firma (paso 9) → `400` (`"hay observaciones pendientes"`).
- **CONAPRES en Marco** — llamar `opinion-conapres` sobre un Convenio Marco → `400` (solo Específico).
- **Cross-tenant** — usuario (no admin) cuyo perfil no corresponde a la universidad solicitante intenta el paso 1 → `403`.
- **Escritura de entidad sin rol** — usuario sin `Administrador RENADS` hace `POST /api/v1/universities/` → `403`.

## Roles por endpoint

| Endpoint | Rol requerido |
|----------|---------------|
| `POST conventions/` | miembro institucional de la entidad solicitante |
| `cambiar-estado` | Administrador RENADS |
| `evaluacion-tecnica` | DIGEP |
| `opinion-conapres`, `campos-clinicos` (POST) | CONAPRES |
| `opinion-juridica` | OGAJ |
| `firma`, `publicacion` | Secretaría General |
| `participantes` (POST) | Administrador RENADS |
| entidades/catálogos (escritura) | Administrador RENADS (catálogos: solo lectura) |
| lecturas (GET) | cualquier usuario autenticado (con alcance institucional) |
