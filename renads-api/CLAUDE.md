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
| **Registrar Internados** | Internos, tutores, sedes docentes, periodos, rotaciones y autorizaciones |
| **Registrar Actividades** | Registro, validación y consulta de actividades docente-asistenciales de internos en sedes |

### Actores principales

- **Institucionales:** MINSA, DIGEP, CONAPRES, OGAJ, Secretaría General, VICEPAS, GORE/GERESA/DIRESA/DIRIS, Universidades, Sedes docentes
- **Operativos:** Autoridad suscrita en Convenio Específico, Tutor/Docente, Interno, Administrador RENADS, Auditor/Supervisor

### Reglas de negocio críticas

1. Convenio Específico requiere Convenio Marco vigente.
2. Internado solo se registra sobre Convenio Específico vigente y autorizado.
3. Rotaciones solo dentro del mismo ámbito geográfico sanitario.
4. Rotaciones requieren autorización de autoridades suscritas en el Convenio Específico.
5. Actividad docente-asistencial debe asociarse a: interno + sede + rotación/periodo + tutor.
6. Todo convenio, internado, rotación y actividad debe ser auditable con trazabilidad completa.

### Requerimientos no funcionales clave para el API

- **Autenticación y autorización** basada en roles y perfiles institucionales (RNF-SEG-01/02/03).
- **Bitácora de auditoría** por operación crítica: usuario, fecha/hora, acción, entidad afectada, valor anterior y nuevo (RNF-AUD-01/02).
- **Gestión documental PDF** adjunta a convenios, actividades y procesos (RNF-DOC-01/02/03).
- **Restricción de acceso** por entidad, rol y ámbito de competencia.
- **Expiración automática de sesión** (RNF-SEG-07).
- **Filtros eficientes** por convenio, universidad, región, sede, interno y periodo (RNF-REN-02).
- **Exportación** de reportes en PDF y Excel (RNF-INT-03).
- **Catálogos parametrizables** sin cambios de código (RNF-MAN-01/02/03).

### Documentación de referencia

Especificaciones funcionales: archivos `0X_*.md` en la raíz del proyecto.

**Schema de base de datos — leer SIEMPRE antes de trabajar en cualquier módulo.** Mantener estos documentos sincronizados con los modelos Django (`convenios/`, `internados/`, `actividades/`):

| Módulo | App | Schema de referencia |
|--------|-----|----------------------|
| M1 — Gestionar Convenios | `convenios` | [docs/db_schema_modulo_01_convenios.md](docs/db_schema_modulo_01_convenios.md) |
| M2 — Registrar Internados | `internados` | [docs/db_schema_modulo_02_internados.md](docs/db_schema_modulo_02_internados.md) |
| M3 — Registrar Actividades | `actividades` | [docs/db_schema_modulo_03_actividades.md](docs/db_schema_modulo_03_actividades.md) |
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
