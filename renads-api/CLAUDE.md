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
- **Partes por tipo (`unidad_ejecutora`/`facultad` en `convenio`):** un **Convenio Marco** no lleva `unidad_ejecutora` ni `facultad` (ambos **nulos**). Un **Convenio Específico** exige **ambos**; la `facultad` debe pertenecer a la universidad del Convenio Marco (`facultad.universidad == convenio_marco.universidad`), o a la universidad propia del Específico para DIRIS sin Marco. Regla única en `services._validar_partes_por_tipo` (aplicada en `crear_convenio` y `actualizar_convenio`, revalidando el estado final del objeto en PATCH parcial). El write serializer expone `unidad_ejecutora`/`facultad` opcionales; el read serializer añade `*_detalle`.
- **Adendas de ampliación (sin límite):** una adenda es una fila `convenio` con `convenio_origen` (self-FK `PROTECT`, `related_name='adendas'`) y `es_adenda=True`, encadenable sin límite (adendas de adendas). Se crea vía `services.crear_adenda` / acción `POST /api/v1/conventions/{id}/adenda` (`AdendaWriteSerializer`: nuevo periodo `fecha_inicio` requerido). Hereda del origen tipo, marco, universidad, órgano, unidad ejecutora, facultad y solicitante; parte en `SOLICITUD_REGISTRADA`. Al pasar una adenda a `VIGENTE`, su `convenio_origen` se marca `AMPLIADO` (salvo `CERRADO`/`ANULADO`/`AMPLIADO`). La **vigencia efectiva** (`selectors.vigencia_efectiva`) es la mayor `fecha_fin` de las adendas vigentes de la cadena, o la `fecha_fin` propia. Filtros: `es_adenda`, `convenio_origen`. Lectura expone `es_adenda`, `convenio_origen`, `adendas`, `vigencia_efectiva`.
- **Requisito de campos clínicos con resolución CONAPRES antes de suscripción:** un Convenio **Específico** no avanza a suscripción (registro de firma o transición a `ENVIADO_SG`) sin ≥1 `campo_clinico_ipress` con `numero_resolucion_conapres` no vacío sobre una sede docente (`ipress.es_sede_docente=True`) de la **unidad ejecutora del convenio** (`ipress.unidad_ejecutora_id == convenio.unidad_ejecutora_id`). Regla en `services._exigir_campos_clinicos_conapres`. Al registrar un campo clínico, la sede debe pertenecer a la unidad ejecutora del convenio (si la tiene) — `services.crear_registro_campo_clinico`.
- **Resolución CONAPRES en `campo_clinico_ipress`:** columnas `numero_resolucion_conapres` (varchar 100) + `fecha_resolucion_conapres` (date), ambas opcionales, expuestas en `ClinicalFieldRegistrationSerializer`.
- **Resoluciones PDF por anexos:** las resoluciones se adjuntan vía `AnnexAttachmentMixin`. `ConventionViewSet` monta el mixin con `annex_actor="CONVENIO"` → `conventions/{id}/annex-upload`/`annex-checklist` para `RESOL_MARCO`/`RESOL_ESPECIFICO`/`RESOL_ADENDA`. `ClinicalFieldRegistrationViewSet` con `annex_actor="CAMPO_CLINICO"` → `clinical-field-registrations/{id}/annex-upload` para `RESOL_CONAPRES`. Los `ANNEX_ACTOR` `CONVENIO` y `CAMPO_CLINICO` y los cuatro `documento_anexo` (`obligatorio=False`) se agregan en `apps/internados`.
- **Partes firmantes por rol (`parte_convenio`, `ConventionParty`):** tabla estructurada de las partes que suscriben el convenio, discriminadas por `rol` (`PARTY_ROLE`: `MINSA`/`UNIVERSIDAD`/`GOBIERNO_REGIONAL`/`UNIDAD_EJECUTORA`/`FACULTAD`), con FKs `organo_directorio` + `organo_representante` + `cargo_ejecutivo` (PROTECT, representante/cargo nullable), `orden` (apoderado de la facultad = `orden=2`) y `es_firmante`; `unique_together (convenio, rol, orden)`, `related_name='partes_firmantes'`. **Coexiste** con `participante_convenio`/`firma` (no los reemplaza). Sincronización idempotente vía `services.sincronizar_partes` + acción `GET/POST /api/v1/conventions/{id}/parties`. Coherencia en el service (`organo_representante.organo_directorio == organo_directorio` y `cargo.organo_directivo == organo_directorio`, omitida si nulos). **Composición por tipo/categoría** (`services._validar_composicion_partes`): Marco Lima (`organo_directorio.categoria == MINSA_DIRIS`) ⇒ `MINSA`+`UNIVERSIDAD`; Marco región (`GOBIERNO_REGIONAL`) ⇒ `MINSA`+`GOBIERNO_REGIONAL`+`UNIVERSIDAD`; Específico ⇒ `UNIDAD_EJECUTORA`+`FACULTAD`. Las dos resoluciones del firmante se **derivan del `organo_representante`**: `numero_resolucion_designacion` + `numero_resolucion_facultades` (nuevo, en `organo_representante` e `historial_organo_representante`).
- **Nomenclatura (reemplaza a `codigo`):** `convenio.codigo` se renombró a `nomenclatura`. Aplica **solo a Convenio Marco** y se asigna al **aprobar DIGEP** (`registrar_evaluacion_tecnica` con `resultado=VALIDADO`, antes de `_set_estado` a `VALIDADO_TECNICAMENTE` y previo a `PENDIENTE_OGAJ`) — gate `services._validar_nomenclatura`. No es editable por PATCH libre (fuera del write serializer y de `editables`); el serializer de la acción `validar-tecnica` acepta `nomenclatura` write-only. Lectura la expone junto a `partes_firmantes`.
- **Generación de PDF (proyecto + expediente):** `apps/convenios/pdf.py` rellena plantillas Word con **docxtpl** y convierte a PDF con **LibreOffice headless** (`soffice --convert-to pdf`; dependencia de sistema, error en español si falta). 5 plantillas en `apps/convenios/templates/convenio/` (`modelo_1_marco_lima`, `modelo_2_marco_region`, `modelo_3_especifico_lima`, `modelo_4_especifico_region`, `adenda`); selección determinista por `(tipo_convenio, es_adenda, organo_directorio.categoria)`. `construir_contexto` arma los datos desde `partes_firmantes` (entidad/razón social, RUC, domicilio — MINSA fijo Av. Salaverry 801; el domicilio de la parte `GOBIERNO_REGIONAL` se deriva de `convenio.gobierno_regional`), `nomenclatura`, carreras de la facultad y `selectors.campos_clinicos_del_especifico`. Endpoints `POST /api/v1/conventions/{id}/generar-proyecto` (anexo `PROYECTO_CONVENIO`/`PROYECTO_ADENDA`) y `generar-expediente` (anexo `EXPEDIENTE`, merge de PDFs adjuntos con **pypdf**); ambos suben al storage y versionan vía `adjuntar_documento`, pasan el gate `IsModuleEnabled`. Los `documento_anexo` `PROYECTO_CONVENIO`/`PROYECTO_ADENDA`/`EXPEDIENTE` (`tipo_actor=CONVENIO`) se siembran en `apps/internados`.

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
- **Gestión documental PDF** adjunta a convenios, actividades y procesos (RNF-DOC-01/02/03). **Almacenamiento de objetos en Cloudflare R2** (S3-compatible, bucket `renads-media`): backend `CloudflareR2Storage` (boto3, presigned URLs `s3v4`) para PDFs (`documento_adjunto`) y `STORAGES["default"]` (`S3Boto3Storage`) para los `ImageField` de logos. Selección en `apps/common/storage.get_document_storage` y en `config/settings/base.py` por precedencia **R2 (`R2_ENABLED`) → GCS legacy (`GCS_ENABLED`) → stub/`FileSystemStorage`**; con R2 deshabilitado el comportamiento previo no cambia. Config vía `R2_*` en `.env`.
- **Restricción de acceso** por entidad, rol y ámbito de competencia.
- **Expiración automática de sesión** (RNF-SEG-07).
- **Filtros eficientes** por convenio, universidad, región, sede, estudiante y periodo (RNF-REN-02).
- **Exportación** de reportes en PDF y Excel (RNF-INT-03).
- **Catálogos parametrizables** sin cambios de código (RNF-MAN-01/02/03). Los catálogos maestros con **CRUD** (escritura solo `Administrador RENADS`, con auditoría) son: `organs` (tabla `organo`; 5 categorías canónicas — `Órgano del MINSA`/`Universidad`/`Gobierno Regional`/`MINSA DIRIS`/`Unidad Ejecutora`, filtrable por `estado`), `health-geographic-scopes`, `executive-positions` (tabla `cargo_ejecutivo`; ya no hereda `Catalog`, FK obligatorio `organo` id → `organs` (`organo_id`, PROTECT, `related_name='cargos_ejecutivos'`) + FK `organo_directivo` id → `organ-directories` (1:N, nullable BD+API), unicidad `(organo_directivo, nombre_masculino)` (el `organo` no entra en la unicidad, se deriva del `organo_directivo`), sin `codigo`, con `nombre_masculino`/`nombre_femenino`, búsqueda por ambos, filtrable por `organo` y `organo_directivo` (con `isnull`), lectura con `organo_detalle` y `organo_directivo_detalle`. **RN-CE (coherencia):** cuando `organo_directivo` está seteado, `organo == organo_directivo.organo` — validado en el serializer custom `_ExecutivePositionSerializer.validate` (el CRUD `_auto_serializer` no ejecuta `Model.clean()`; soporta PATCH parcial); cargo global (`organo_directivo` nulo) solo exige el `organo` obligatorio), `authorization-types`, `academic-levels`, `categories`, `classification-types`, más la jerarquía geográfica `networks` (`red`) y `micro-networks` (`microred`) (todos en `apps/convenios`, promovidos de solo lectura a `ENTITY_VIEWSETS`) y `annex-documents` (`apps/internados`, filtrable por `tipo_actor`). Se **retiró** `document-types` (modelo `DocumentType` eliminado; sus tipos genéricos viven ahora en `documento_anexo` con `tipo_actor` vacío) y `organ-types` (modelo `OrganType`/tabla `tipo_organo` eliminados; sus filas se migraron a `organo_directorio` con la `categoria` correspondiente). El resto de catálogos siguen de solo lectura.
- **Directorio de órganos y representantes (Módulo 1):** `organ-directories` (tabla `organo_directorio`, entidad CRUD **sin logo** — catálogo unificado de órganos/tipos discriminado por `categoria` (`ORGANO_MINSA`/`UNIVERSIDAD`/`GOBIERNO_REGIONAL`/`MINSA_DIRIS`/`UNIDAD_EJECUTORA`); sin FK `organo`/`tipo_organo`/`ubigeo` ni `referencia_logo`; el GORE ya no vive aquí (se trasladó a `convenio.gobierno_regional`); único por `(organo, nombre)`; filtrable por `categoria`/`activo`); `organ-representatives` (tabla `organo_representante`, FK directo a `organo_directorio` — reemplaza `representatives`/`university-authorities`; la coherencia cargo↔órgano compara por **entidad** (`cargo.organo_directivo_id == organo_directorio_id`; los cargos legacy sin `organo_directivo` no se validan); al designar un nuevo representante para el mismo `(organo_directorio, cargo_ejecutivo)` el service `registrar_organo_representante` da de baja al anterior y lo copia a `organ-representative-history`, tabla `historial_organo_representante`, solo lectura). `conventions` referencia `organo_directorio` y `gobierno_regional` (FK nullable `PROTECT` `convenio.gobierno_regional_id`, solo Convenio Marco regional; regla `services._validar_gobierno_regional_por_tipo` en `crear_convenio`/`actualizar_convenio`; la adenda lo hereda del origen); `evaluacion_tecnica` referencia `organo_directorio` (SET_NULL). Un `organo_directorio` es un **órgano directivo** que agrupa 1..N `cargo_ejecutivo` (relación 1:N vía `cargo_ejecutivo.organo_directivo`; la tabla puente `organo_directorio_cargo` fue retirada). `executing-units` (tabla `unidad_ejecutora`): `tipo_organo` es FK a `organo_directorio` (`limit_choices_to` categoría `UNIDAD_EJECUTORA`) y `gobierno_regional` FK a `gobierno_regional`; CRUD con logo, filtros `tipo_organo`/`gobierno_regional`/`activo`, búsqueda `nombre`/`codigo`. `universities`: `tipo_entidad` es FK a `organo_directorio` (`limit_choices_to` categoría `UNIVERSIDAD`). `regional-governments` (tabla `gobierno_regional`) suma `ubigeo` (FK opcional) y `sigla`; CRUD con logo, filtros `region`/`ubigeo`/`activo`, lectura con `ubigeo_detalle`. `faculties` (tabla `facultad`) suma `referencia_logo`, `ubigeo` y `direccion`; CRUD con logo (`upload-logo`/`logo-url`), filtros `universidad`/`ubigeo`/`activo`, búsqueda `nombre`/`direccion`. **RN-1 (Convenio Marco):** solo `organo_directorio.categoria == GOBIERNO_REGIONAL` puede solicitar Marco; `MINSA_DIRIS` (DIRIS) está exenta de Marco — regla en `services.crear_convenio`. Endpoints retirados (404): `regional-organs`, `minsa-organs`, `representatives`, `university-authorities`, `document-types`, `organ-types`.
- **Carreras por universidad (Módulo 1):** `university-careers` (tabla puente `universidad_carrera`, `UniversityCareer`; FK `universidad` + `carrera_profesional` + **`facultad`** (PROTECT, **obligatoria en BD y API** desde migración `0032`), `unique_together (universidad, carrera_profesional)`; validación `facultad.universidad == universidad` (RN-FC-02); CRUD escritura solo `Administrador RENADS`; filtros `universidad`/`carrera_profesional`/`facultad`/`activo`; lectura expone `universidad_detalle`, `carrera_profesional_detalle`, `facultad_detalle`). **RN-FC-04 (carrera única por universidad):** una carrera pertenece a una sola facultad por universidad; asignada+activa no puede elegirse desde otra facultad (CRUD directo → 400 vía `UniqueTogetherValidator`; sync → 400 en `sincronizar_carreras_facultad`). Si se da de baja (`activo=False`) queda libre para otra facultad. Acción en lote `POST /api/v1/faculties/{id}/careers` (`{carreras:[ids]}`, sincronización idempotente por facultad vía `services.sincronizar_carreras_facultad`: deriva `universidad` de la facultad, da de alta/reactiva las carreras enviadas y de baja (`activo=False`) las que ya no estén; bloquea tomar una carrera activa de otra facultad).

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
