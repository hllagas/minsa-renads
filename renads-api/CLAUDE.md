# CLAUDE.md

Este archivo provee instrucciones a Claude Code (claude.ai/code) para trabajar en este repositorio.

## Metodología de trabajo — SDD (obligatoria)

El proyecto se desarrolla con **Spec Driven Development (SDD)** coordinado por el agente **`orchestrator`** (`.claude/agents/orchestrator.md`). **Para toda solicitud de desarrollo de un módulo o feature, seguir SIEMPRE el flujo del orquestador:**

```
orchestrator → spec → implement → validator → (repetir implement↔validator hasta OK)
```

- **`orchestrator`** — coordina; no escribe código ni specs.
- **`spec`** — crea las tareas exactas por módulo en `spec/<modulo>.md`.
- **`implement`** — desarrolla el código en `apps/<modulo>/` según el spec.
- **`validator`** — revisa contra spec/arquitectura/schema; genera `spec/<modulo>.validacion.md` o confirma.

Fuentes de verdad: `docs/alcance_mvp.md`, `docs/arquitectura_desarrollo.md` y los `docs/db_schema_*.md`. No avanzar a implementación sin spec; no cerrar un módulo sin validación sin errores.

## Contexto del proyecto

**RENADS — Registro Nacional de Articulación Docencia-Servicio en Salud**

Sistema de información del MINSA (Perú) para registrar, controlar y dar seguimiento a la articulación entre entidades del sector salud y universidades que desarrollan actividades de docencia-servicio en salud.

### Módulos

| Módulo | Responsabilidad |
|--------|----------------|
| **Gestionar Convenios** | Ciclo de vida de Convenios Marco y Específicos: documentos PDF, evaluaciones, opiniones (DIGEP, CONAPRES, OGAJ), firmas, publicación, vigencia y cierre |
| **Registrar Internados** | Estudiantes, tutores, sedes docentes, periodos, rotaciones y autorizaciones |
| **Registrar Actividades** | Registro, validación y consulta de actividades docente-asistenciales de estudiantes en sedes |
| **Calendario administrativo** | Agenda de hitos/ventanas del proceso y **enforcement temporal de escritura** por módulo: una actividad de calendario con ventana de fechas habilita o bloquea la escritura de los modelos que gobierna (`content_types`) mientras esté vigente |

### Actores principales

- **Institucionales:** MINSA, DIGEP, CONAPRES, OGAJ, Secretaría General, VICEPAS, GORE/GERESA/DIRESA/DIRIS, Universidades, Sedes docentes
- **Operativos:** Autoridad suscrita en Convenio Específico, Tutor/Docente, Estudiante, Administrador RENADS, Auditor/Supervisor

### Reglas de negocio críticas

1. Convenio Específico requiere Convenio Marco vigente — **excepto las DIRIS** (Lima Metropolitana), que no requieren Convenio Marco.
2. Internado solo se registra sobre Convenio Específico vigente y autorizado.
3. Rotaciones solo dentro del mismo ámbito geográfico sanitario.
4. Rotaciones requieren autorización de autoridades suscritas en el Convenio Específico.
5. Actividad docente-asistencial debe asociarse a: estudiante + sede + rotación/periodo + tutor.
6. Todo convenio, internado, rotación y actividad debe ser auditable con trazabilidad completa.

#### Reglas del módulo Gestionar Convenios

- Solo la **GERESA** o la **DIRESA** pueden solicitar un **Convenio Marco**. Las **DIRIS** no requieren Convenio Marco para solicitar un **Convenio Específico**.
- La **opinión jurídica (OGAJ)** se solicita **solo para Convenios Marco**.
- La **opinión favorable (CONAPRES)** se solicita **solo para Convenios Específicos**.
- **CONAPRES autoriza y registra las IPRESS como sedes docentes** que cumplan los criterios de evaluación: establecimiento **asistencial**, que **pertenezca al MINSA o a la sanidad de las Fuerzas Armadas/Policiales**, y de gestión **pública**.
- **CONAPRES autoriza y registra el total de campos clínicos por cada sede docente según carrera profesional.**
- La **GERESA, DIRESA o DIRIS** asigna la **cantidad de campos clínicos por universidad y carrera profesional**, para las universidades con Convenios Específicos aprobados en el **mismo ámbito geográfico sanitario**.
- **Campos clínicos (dos sub-módulos, dos tablas/endpoints):**
  - **Registro de Campos Clínicos = CONAPRES** — tabla `campo_clinico_ipress` (`ClinicalFieldRegistration`), endpoint `/api/v1/clinical-field-registrations/` (escritura solo rol `CONAPRES`, `IsConapresOrReadOnly`). CONAPRES registra el **total** por sede docente (`ipress`, `es_sede_docente=True`) + carrera en `campos_clinicos_registrados`. `campos_clinicos_asignados` es un acumulador Σ (default 0, **solo lectura** en la API); el serializer expone `disponibilidad = registrados − asignados`. Filtros: `convenio`, `ipress`, `carrera_profesional`, `especialidad`. **Flujo del convenio:** crear un registro avanza el Convenio Específico al estado `CAMPOS_CLINICOS_DEFINIDOS` (orden 10) vía `services._avanzar_estado` — *forward-only* e idempotente: no regresa un convenio ya en un estado posterior (p. ej. `VIGENTE`). Reemplaza el `_set_estado` que hacía el retirado `definir_campo_clinico`.
  - **Asignación de Campos Clínicos = Órgano Regional** — tabla `campo_clinico_ipress_universidad` (`ClinicalFieldAllocation`), endpoint `/api/v1/clinical-field-allocations/` (escritura solo grupo `Gobierno Regional`, `IsRegionalOrganOrReadOnly`). El Órgano Regional (GERESA/DIRESA/DIRIS) asigna cupos **por universidad** contra un registro (`campo_clinico_ipress`, `related_name='asignaciones'`) en `campos_clinicos_autorizados`. Filtros: `campo_clinico_ipress`, `convenio`, `ipress`, `carrera_profesional`, `universidad`. **Reemplaza** la action anidada `conventions/{id}/campos-clinicos` (retirada).
  - **Regla de disponibilidad y acumulador:** `campos_clinicos_autorizados ≤ campos_clinicos_registrados − Σ autorizados de las demás asignaciones del mismo registro`; además exige convenio **Específico + vigente**, `convenio.universidad == asignacion.universidad` e `ipress`/`carrera` coherentes con el registro padre. El acumulador `campos_clinicos_asignados` del registro padre se **recalcula** en el service tras cada create/update/delete de asignación.
- **RN-25 (interno → asignación por universidad):** `Internship.campo_clinico` es FK a `ClinicalFieldAllocation` (`db_column='campo_clinico_id'`, `PROTECT`) — el interno se ata a la **asignación por universidad**, no al registro global. RN-13 valida contra `campo_clinico.campos_clinicos_autorizados`; el chequeo de ámbito geográfico sanitario deriva de `interno.campo_clinico.ipress.ambito_geografico_sanitario_id`.

#### Reglas del módulo Registrar Internados

- El **registro de estudiantes** tiene **doble modalidad**: **individual** (contemplada) y **masiva** mediante un **archivo Excel** con la estructura de carga definida (ver `docs/db_schema_modulo_02_internados.md` §carga masiva y `spec/internados.md`).
- La **universidad** registra internos en los **campos clínicos disponibles** de cada sede docente y carrera profesional definidos previamente en los Convenios Específicos.
- **Orden de prelación** para la asignación de internos: por **orden de mérito** según `nota_promedio_ponderado`, de **mayor a menor**.
- **RN-19 (periodo académico vs. especialidad):** según el nivel académico de la carrera del estudiante, se registra **uno u otro** — nivel `PREGRADO` ⇒ `periodo_academico` obligatorio y `especialidad` nula; cualquier otro nivel (`SEGUNDA_ESPECIALIDAD`/`MAESTRIA`/`DOCTORADO`/…) ⇒ `especialidad` obligatoria y `periodo_academico` nulo. Regla única en `services.validar_regla_periodo_especialidad`, compartida por el registro individual y el masivo.
- **Documentos requeridos por actor (`documento_anexo`, ex `documentos_anexos`):** catálogo maestro de los documentos que cada actor debe adjuntar, discriminado por `tipo_actor`: `INTERNO` ⇒ declaraciones juradas del estudiante (veracidad de datos, antecedentes, salud, confidencialidad); `REPRESENTANTE` (incluye autoridades de universidad y de CONAPRES) ⇒ resolución del cargo y documento de identidad; **`tipo_actor` vacío** para los tipos genéricos absorbidos (`ANEXO`/`CONVENIO`/`RESOLUCION`, desde la retirada de `DocumentType`). Su CRUD vive en `/api/v1/annex-documents/` (filtrable por `tipo_actor`). El **adjunto real** del PDF por entidad se sube y versiona como `documento_adjunto` (tabla `documento_adjunto`, ex `documento`; FK **obligatoria** `documento_adjunto.documento_anexo_id`, **único discriminador** de versionado por `(objeto, documento_anexo)`) vía las acciones `annex-upload`/`annex-checklist` en `interns` (actor `INTERNO` — sobre el **internado**, no el estudiante) y `organ-representatives` (`REPRESENTANTE`). Detalle de endpoints en `docs/api_almacenamiento_frontend.md`. Los estados de presentación/aprobación del anexo (revisado/observado) siguen fuera de alcance del MVP.
- **RN-20 (registro por universidad con alcance):** el registro de internos lo efectúa el rol `Universidad`; solo puede registrar/ver internos de las universidades dentro de su ámbito institucional (`perfil_usuario_entidad`, 1..N universidades). Superusuario y `Administrador RENADS` exentos.
- **RN-21 (unicidad de interno por DNI):** un estudiante no puede tener más de un internado **vigente**. Estados bloqueantes: `REGISTRADO`, `PENDIENTE_VALIDACION`, `OBSERVADO`, `VALIDADO`, `ACTIVO`, `EN_ROTACION_*`. Estados liberadores (permiten nuevo registro): `SUSPENDIDO`, `RETIRADO`, `CULMINADO`, `ANULADO`. Regla en `services.tiene_internado_vigente`.
- **Contacto de emergencia:** vive en la tabla `interno` (`Internship`), no en `estudiante` — aplica al internado concreto. Se registra/actualiza al crear o editar el internado (`interns/`); ya no forma parte de la carga masiva de estudiantes.
- **RN-22 (onboarding del interno):** al registrar el internado se crea/reutiliza un `User` (`username = numero_documento`, contraseña temporal, grupo `Interno`, `perfil_usuario_entidad` sobre su `Student`) con solo lectura de sus datos y adjunto de sus DJ **sobre su internado** (`interns/{id}/annex-upload/`). El rol `Interno` accede a su propio internado (alcance por perfil sobre `Student`) para adjuntar las DJ. Flag `debe_cambiar_password` en la tabla `seguridad_usuario` (modelo `UserSecurity`, app `apps.common`) — expuesto como claim del JWT y en `GET /api/v1/auth/me/`; se limpia en `POST /api/v1/auth/me/cambiar-password/`. Se notifica por correo al interno (best-effort post-commit; backend consola en dev, SMTP en prod).
- **RN-23 (estado de declaraciones juradas):** `interno.estado_declaraciones` (`PENDIENTE`/`COMPLETAS`/`OBSERVADAS`/`VALIDADAS`). `PENDIENTE→COMPLETAS` automático al completar las DJ obligatorias del actor `INTERNO` (fuente única `services.recalcular_estado_declaraciones`, enganchada tras `annex-upload`); revisión humana `COMPLETAS→VALIDADAS`/`OBSERVADAS` en `POST /api/v1/interns/{id}/revisar-declaraciones/` (rol `Universidad`/`Administrador RENADS`). El internado no pasa a `ACTIVO` sin `estado_declaraciones = VALIDADAS`.
- **RN-24 (universidades del tutor):** un **tutor** pertenece de **1 a 2 universidades** (tope de negocio) vía la tabla puente `tutor_universidad` (M2M `Tutor.universidades`). Regla única en `services.validar_universidades_tutor`, aplicada por `TutorSerializer` en create/update; el endpoint `/api/v1/tutors/` acepta y filtra por `universidades`.

#### Reglas del módulo Calendario administrativo

- **RN-26 (la ventana habilita la escritura del módulo):** una `CalendarActivity` (app `apps.calendario`, tabla `actividad_calendario`) con `controla_acceso = True` y `activo = True` **gobierna la escritura** (`POST`/`PUT`/`PATCH`/`DELETE`) de los modelos que referencia por M2M `content_types` (→ `django_content_type`). La escritura de un módulo gobernado se permite **solo** si existe ≥1 **ventana vigente**: `fecha_inicio <= hoy` y (`fecha_fin` NULL **o** `fecha_fin >= hoy`). **`fecha_fin` NULL = ventana abierta** (sin cierre). Semántica **OR** entre ventanas del mismo `ContentType` (basta una vigente). Módulo no referenciado ⇒ *pass-through* (nunca se bloquea). El campo `responsables` de `actividad_calendario` es **texto libre** (no roles/grupos; no existe puente `actividad_calendario_responsable`).
  - **Fuente única temporal — selector `apps/calendario/selectors.py`:** `content_types_controlados(now)` (quién está gobernado; sin filtro de fechas), `content_types_habilitados(now)` (subconjunto con ventana vigente) y `esta_habilitado(ct_id, now)` (`True` si no gobernado o con ventana vigente). Consumido por el permiso de escritura y por `/auth/me/`.
  - **Gate de escritura — `IsModuleEnabled` (`apps/common/permissions.py`):** *opt-in* por atributo de vista `module_content_type = (app_label, model)`; si la vista no lo declara ⇒ *pass-through*. Solo gatea escritura (lectura `SAFE_METHODS` siempre libre); **exentos SOLO** superusuario y rol `Administrador RENADS` (ningún otro rol exento). Fuera de ventana deniega con **403** y `code = "MODULO_FUERA_DE_VENTANA"`. **ViewSets instrumentados:** `ConventionViewSet`, `InternshipViewSet`, `TeachingActivityViewSet`.
  - **Exposición al frontend — `/auth/me/`:** `MeSerializer` (`apps/common/serializers.py`) agrega `modulos_habilitados` y `modulos_bloqueados`, cada uno lista de `{ app_label, model, content_type_id }` derivada del mismo selector. Reflejan el **estado temporal del módulo**, no la exención del admin (para admin/superusuario un módulo fuera de ventana aparece en `modulos_bloqueados` aunque el gate no lo bloquee).
  - **Endpoints:** `/api/v1/content-types/` (solo lectura, `{id, app_label, model, verbose_name}`, `IsAuthenticated`) alimenta el selector `content_types[]`; `/api/v1/calendar-activities/` (CRUD, escritura solo `Administrador RENADS` con auditoría; lectura expone `content_types_detalle`, con `responsables` como texto libre en lectura y escritura; filtros `controla_acceso`, `activo`, `content_types`, rango de fechas). Detalle en `docs/db_schema_modulo_04_calendario.md` y `docs/api_accesos_frontend.md`.

### Requerimientos no funcionales clave para el API

- **Autenticación y autorización** basada en roles y perfiles institucionales (RNF-SEG-01/02/03).
- **Bitácora de auditoría** por operación crítica: usuario, fecha/hora, acción, entidad afectada, valor anterior y nuevo (RNF-AUD-01/02).
- **Gestión documental PDF** adjunta a convenios, actividades y procesos (RNF-DOC-01/02/03).
- **Restricción de acceso** por entidad, rol y ámbito de competencia.
- **Expiración automática de sesión** (RNF-SEG-07).
- **Filtros eficientes** por convenio, universidad, región, sede, estudiante y periodo (RNF-REN-02).
- **Exportación** de reportes en PDF y Excel (RNF-INT-03).
- **Catálogos parametrizables** sin cambios de código (RNF-MAN-01/02/03). Los catálogos maestros con **CRUD** (escritura solo `Administrador RENADS`, con auditoría) son: `organs` (tabla `organo`; 4 categorías canónicas, filtrable por `estado`), `health-geographic-scopes`, `executive-positions` (tabla `cargo_ejecutivo`; ya no hereda `Catalog`, FK `organo` id → `organs`, unicidad `(organo, codigo)`, filtrable por `organo`), `organ-types` (filtrable por `organo`; ahora `organo` es FK id → `organs`), `authorization-types`, `academic-levels`, `categories`, `classification-types`, más la jerarquía geográfica `networks` (`red`) y `micro-networks` (`microred`) (todos en `apps/convenios`, promovidos de solo lectura a `ENTITY_VIEWSETS`) y `annex-documents` (`apps/internados`, filtrable por `tipo_actor`). Se **retiró** `document-types` (modelo `DocumentType` eliminado; sus tipos genéricos viven ahora en `documento_anexo` con `tipo_actor` vacío). El resto de catálogos siguen de solo lectura.
- **Directorio de órganos y representantes (Módulo 1):** `organ-directories` (tabla `organo_directorio`, entidad CRUD con logo — unifica los antiguos `regional-organs`/`minsa-organs`, filtrable por `organo`/`tipo_organo`/`gobierno_regional`); `organ-representatives` (tabla `organo_representante`, FK directo a `organo_directorio` — reemplaza `representatives`/`university-authorities`; al designar un nuevo representante para el mismo `(organo_directorio, cargo_ejecutivo)` el service `registrar_organo_representante` da de baja al anterior y lo copia a `organ-representative-history`, tabla `historial_organo_representante`, solo lectura). `conventions` referencia `organo_directorio`; `evaluacion_tecnica` referencia `organo_directorio` (SET_NULL). `executing-units` (tabla `unidad_ejecutora`) tiene campos `codigo`, `nombre`, `tipo_organo`, `gobierno_regional`, `direccion`, `ubigeo`, `referencia_logo`, `activo`: `tipo_organo` es FK a `tipo_organo` (`limit_choices_to` categoría `Unidad Ejecutora`) y `gobierno_regional` FK a `gobierno_regional`; CRUD con logo, filtros `tipo_organo`/`gobierno_regional`/`activo`, búsqueda `nombre`/`codigo`. Endpoints retirados (404): `regional-organs`, `minsa-organs`, `representatives`, `university-authorities`, `document-types`.
- **Carreras por universidad (Módulo 1):** `university-careers` (tabla puente `universidad_carrera`, `UniversityCareer`; FK `universidad` + `carrera_profesional`, `unique_together`; CRUD escritura solo `Administrador RENADS`; filtros `universidad`/`carrera_profesional`/`activo`; lectura expone `universidad_detalle` y `carrera_profesional_detalle`).

### Documentación de referencia

Especificaciones funcionales: archivos `0X_*.md` en la raíz del proyecto.

**Schema de base de datos — leer SIEMPRE antes de trabajar en cualquier módulo.** Mantener estos documentos sincronizados con los modelos Django (`convenios/`, `internados/`, `actividades/`):

| Módulo | App | Schema de referencia |
|--------|-----|----------------------|
| M1 — Gestionar Convenios | `convenios` | [docs/db_schema_modulo_01_convenios.md](docs/db_schema_modulo_01_convenios.md) |
| M2 — Registrar Internados | `internados` | [docs/db_schema_modulo_02_internados.md](docs/db_schema_modulo_02_internados.md) |
| M3 — Registrar Actividades | `actividades` | [docs/db_schema_modulo_03_actividades.md](docs/db_schema_modulo_03_actividades.md) |
| M4 — Calendario administrativo | `calendario` | [docs/db_schema_modulo_04_calendario.md](docs/db_schema_modulo_04_calendario.md) |
| Diagrama ER global | — | [docs/db_schema_er_global.md](docs/db_schema_er_global.md) |
| Arquitectura de desarrollo (MVP) | — | [docs/arquitectura_desarrollo.md](docs/arquitectura_desarrollo.md) |
| Alcance del MVP + metodología SDD | — | [docs/alcance_mvp.md](docs/alcance_mvp.md) |

> Antes de crear/modificar modelos, serializers, vistas o migraciones, revisar el schema del módulo correspondiente. Si un cambio de modelo altera tablas/columnas, **actualizar el `.md` del módulo** en el mismo cambio.

## Reglas del proyecto

- **Comunicación y documentación:** siempre en español — respuestas, comentarios en código, docstrings, archivos `.md`, mensajes de error orientados al usuario.
- **Código y estructura:** siempre en inglés — nombres de variables, funciones, clases, endpoints, ramas de git, mensajes de commit.
- **Modelo de datos:** nombres de tablas, columnas y la descripción de cada campo en **español**. Todo lo demás del código sigue en inglés.
- **Apps Django (carpetas):** las apps de módulo viven dentro de `apps/` y sus nombres van en **español** — `apps/convenios`, `apps/internados`, `apps/actividades`. En `INSTALLED_APPS` se registran como `apps.convenios`, etc.; cada `AppConfig` fija `label` (`convenios`…) para mantener el `app_label`. Imports cruzados: `from apps.convenios.models import ...`. Excepción puntual a la regla de carpetas en inglés; otras carpetas/paquetes siguen en inglés.
- **Entorno virtual:** antes de ejecutar cualquier comando dentro del proyecto, activar el entorno virtual con `.venv\Scripts\Activate.ps1`.
- **Servidor de desarrollo:** nunca ejecutar `python manage.py runserver` — ese comando siempre lo corre el usuario manualmente.

## Comandos

```bash
# Activar entorno virtual (PowerShell)
.venv\Scripts\Activate.ps1

# Ejecutar todas las pruebas
python manage.py test

# Ejecutar pruebas de una app específica
python manage.py test products

# Migraciones
python manage.py makemigrations
python manage.py migrate
```

## Arquitectura

Django 6.0.6 + Django REST Framework 3.17.1. Python 3.14.

**Estructura:**
- `config/` — configuración del proyecto, URLconf raíz, wsgi/asgi
- `products/` — única app existente; modelos, vistas y pruebas son stubs vacíos por ahora

**Base de datos:** SQLite en desarrollo (`db.sqlite3`). `psycopg2-binary` está instalado — PostgreSQL es el backend previsto para producción.

**Configuración de entorno:** `python-decouple` está instalado pero `config/settings.py` aún usa valores hardcodeados. Migrar secrets y config de BD a un archivo `.env` antes de agregar valores sensibles.

## Skills y commands — uso obligatorio

Skills en `.claude/skills/`, commands en `.claude/commands/`. **Invocar siempre** en los contextos indicados:

- **`/fix-types`** — invocar cuando haya errores de mypy o problemas de tipos. No corregir tipos manualmente sin pasar por esta skill.
- **`/upgrade-python-deps`** — invocar al actualizar dependencias Python o antes de release. No tocar `requirements.txt` manualmente.
- **`/upgrade-js-deps`** — invocar si el proyecto agrega frontend y el usuario pide actualizar deps JS.
- **`/code-review`** — invocar al trabajar con modelos, vistas, serializers, migraciones, tests o cualquier tarea Django/DRF. Ejecutar antes de dar por terminada cualquier implementación.

## Pendientes antes de comenzar desarrollo real

- `products` no está en `INSTALLED_APPS`
- `rest_framework` no está en `INSTALLED_APPS`
- `SECRET_KEY` hardcodeado en `settings.py` — mover a `.env` vía `decouple.config()`
- No existen rutas URL más allá de `/admin/`
