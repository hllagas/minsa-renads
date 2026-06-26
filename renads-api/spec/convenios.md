# Spec — Módulo `convenios` (Gestionar Convenios)

Lista de tareas exactas para implementar el módulo `apps/convenios/` según
[arquitectura](../docs/arquitectura_desarrollo.md) y [schema M1](../docs/db_schema_modulo_01_convenios.md).
Producido por el agente **spec** (SDD). El agente **implement** ejecuta estas tareas en orden; el **validator** revisa contra este documento.

## Resumen

Exponer vía DRF (bajo `/api/v1/`) los recursos del módulo: catálogos (solo lectura), entidades organizacionales/académicas, núcleo de convenios y flujo del convenio. La lógica de negocio (reglas RN) va en `services.py`; las lecturas en `selectors.py`; los ViewSets son delgados. Auth JWT ya existe (Fase 1-2); permisos base en `apps/common/`.

**Convenciones:** clases en inglés; campos/tablas/`help_text` en español; **endpoints en inglés**; docstrings en español. No crear archivos de testing (fuera de alcance MVP).

**Entidades del módulo** (modelos en `apps/convenios/models.py`):
- Catálogos (18): `Region`, `HealthGeographicScope`, `ConventionType`, `ConventionStatus`, `DocumentType`, `UniversityManagementType`, `UniversityEntityType`, `AuthorizationType`, `AcademicLevel`, `Specialty`, `SigningAuthorityType`, `RegionalOrganType`, `ExecutingUnitType`, `MinsaOrganType`, `ExecutivePosition`, `ObservationReason`, `RejectionReason`, `ClosureReason`.
- Entidades: `RegionalGovernment`, `RegionalOrgan`, `ExecutingUnit`, `Ipress`, `MinsaOrgan`, `Conapres`, `Representative`, `University`, `UniversityAuthority`, `Faculty`, `ProfessionalCareer`, `UniversityCampus`, `UserEntityProfile`.
- Núcleo: `ConventionTemplate`, `Convention`, `ConventionParticipant`, `ConventionStatusHistory`.
- Flujo: `TechnicalEvaluation`, `ConapresOpinion`, `ClinicalField`, `LegalOpinion`, `Signature`, `Publication`.
- Transversal: `Document`, `AuditLog`.

---

## T1 — Serializers (`apps/convenios/serializers.py`)

- **T1.1** Catálogos: un `ModelSerializer` de solo lectura por catálogo (campos `id`, `codigo`, `nombre`, `activo` + extras como `anios_vigencia`, `aplica_a`, `orden`). Pueden agruparse con una clase base.
- **T1.2** Entidades organizacionales y académicas: `ModelSerializer` por entidad (`RegionalGovernment`, `RegionalOrgan`, `ExecutingUnit`, `Ipress`, `MinsaOrgan`, `Conapres`, `Representative`, `University`, `UniversityAuthority`, `Faculty`, `ProfessionalCareer`, `UniversityCampus`). FKs por `id`; incluir representación legible (`__str__`) en lectura cuando ayude.
- **T1.3** `Representative` (polimórfico): exponer `tipo_contenido` (modelo) + `id_objeto`; validar que el `content_type` apunte a una entidad permitida (`organo_minsa`, `organo_regional`, `unidad_ejecutora`, `ipress`, `conapres`).
- **T1.4** `Convention`: separar `ConventionReadSerializer` (anida tipo, estado, solicitante legible) y `ConventionWriteSerializer` (acepta FKs + `solicitante_tipo_contenido`/`solicitante_id_objeto`). `estado_actual`, `fecha_fin`, `creado_por` son de solo lectura (los fija el service).
- **T1.5** Núcleo y flujo: serializers para `ConventionTemplate`, `ConventionParticipant`, `ConventionStatusHistory`, `TechnicalEvaluation`, `ConapresOpinion`, `ClinicalField`, `LegalOpinion`, `Signature`, `Publication`. Campos calculados/estado/responsable como solo lectura.
- **T1.6** `Document`: serializer con `tipo_documento`, `tipo_contenido`+`id_objeto`, `referencia_externa`, `version`, `estado`; `cargado_por`/`cargado_en` solo lectura.

**Criterio de aceptación:** cada entidad tiene serializer; `Convention` tiene read/write; campos controlados por services marcados `read_only`.

---

## T2 — Selectors (`apps/convenios/selectors.py`)

- **T2.1** `convenios_visibles(usuario)`: queryset de `Convention` filtrado por alcance institucional (entidad solicitante/participante dentro de las entidades del usuario; superusuario ve todo). Usar helpers de `apps/common/selectors.py`.
- **T2.2** `historial_convenio(convenio)`: `ConventionStatusHistory` ordenado por `cambiado_en`.
- **T2.3** `documentos_de(objeto)`: documentos (`Document`) asociados a un objeto vía relación genérica.
- **T2.4** Selectores de apoyo para campos clínicos por convenio y participantes/firmantes por convenio.

**Criterio:** las vistas no construyen querysets de negocio; usan selectors. El alcance institucional se aplica en `convenios_visibles`.

---

## T3 — Services (`apps/convenios/services.py`)

Toda escritura corre en `transaction.atomic()`, registra en `bitacora_auditoria` (helper común) y, si cambia estado, en `historial_estado_convenio`.

- **T3.1** `crear_convenio(datos, usuario)`:
  - **RN-3:** si `tipo_convenio == ESPECIFICO`, exige `convenio_marco` existente y **vigente** (estado en {`VIGENTE`,`PUBLICADO`,`SUSCRITO`}); si no, error de validación.
  - Calcular `fecha_fin = fecha_inicio + anios_vigencia` del tipo (4 Marco / 3 Específico) cuando haya `fecha_inicio`.
  - Estado inicial `SOLICITUD_REGISTRADA`; `creado_por = usuario`.
- **T3.2** `cambiar_estado(convenio, nuevo_estado_codigo, usuario, observacion="")`: valida que el estado exista; respeta `aplica_a` (estados `ESPECIFICO` solo para específicos); actualiza `estado_actual` y registra historial + auditoría.
- **T3.3** `registrar_evaluacion_tecnica(convenio, datos, usuario)`: crea `TechnicalEvaluation`; si `resultado=VALIDADO` mueve a `VALIDADO_TECNICAMENTE`, si `OBSERVADO` a `OBSERVADO_DIGEP`.
- **T3.4** `registrar_opinion_conapres(convenio, datos, usuario)`: **solo Específico**; crea `ConapresOpinion`; ajusta estado (`PENDIENTE_CONAPRES`/`CONAPRES_FAVORABLE`/`CONAPRES_OBSERVADO`).
- **T3.5** `definir_campo_clinico(convenio, datos, usuario)`: **solo Específico**; crea `ClinicalField`; al menos uno → estado `CAMPOS_CLINICOS_DEFINIDOS`. Validar que `cantidad_maxima ≤ convenio.max_campos_clinicos` si está definido.
- **T3.6** `registrar_opinion_juridica(convenio, datos, usuario)`: crea `LegalOpinion`; ajusta estado (`OGAJ_FAVORABLE`/`OGAJ_OBSERVADO`).
- **T3.7** `registrar_firma(convenio, datos, usuario)`: **bloquea si hay observaciones pendientes** (evaluación técnica `OBSERVADO`, opinión CONAPRES/OGAJ `OBSERVADO` sin subsanar); crea `Signature` y avanza estado según firmante (`FIRMADO_MINSA`/`FIRMADO_EXTERNOS`).
- **T3.8** `publicar_convenio(convenio, datos, usuario)`: crea `Publication`; estado `PUBLICADO`→`VIGENTE`.
- **T3.9** `agregar_participante(convenio, datos)` / `quitar_participante`.

**Criterio:** cada RN del §6 del módulo está cubierta por un service; ningún cambio de estado ocurre fuera de services; auditoría e historial siempre registrados.

---

## T4 — ViewSets (`apps/convenios/views.py`)

- **T4.1** Catálogos: `ReadOnlyModelViewSet` por catálogo (list/retrieve).
- **T4.2** Entidades: `ModelViewSet` (CRUD) por entidad organizacional/académica.
- **T4.3** `ConventionViewSet` (`ModelViewSet`): usa `ConventionReadSerializer`/`ConventionWriteSerializer` según acción; `get_queryset` = `selectors.convenios_visibles(user)`; `create`/`update` delegan en services. Acciones extra (`@action`, métodos POST):
  - `cambiar-estado`, `evaluacion-tecnica`, `opinion-conapres`, `campos-clinicos`, `opinion-juridica`, `firma`, `publicacion`, `participantes`, `historial`, `documentos`.
- **T4.4** Flujo: ViewSets de lectura/escritura para `TechnicalEvaluation`, `ConapresOpinion`, `ClinicalField`, `LegalOpinion`, `Signature`, `Publication` (alternativamente solo accesibles vía las acciones de `ConventionViewSet`; el implement decide pero debe quedar consistente con el router).
- **T4.5** `DocumentViewSet`: subir/listar documentos (la subida usará el service `adjuntar_documento` cuando exista el storage; por ahora acepta `referencia_externa`).

**Criterio:** ViewSets delgados (sin lógica de negocio); escritura vía services; lectura vía selectors; serializer read/write correcto por acción.

---

## T5 — Permissions (`apps/convenios/permissions.py`)

- **T5.1** Por defecto `IsAuthenticated` (global) + `IsInstitutionalMember` (de `apps/common`).
- **T5.2** `ConventionViewSet` implementa `get_entity_reference(obj)` devolviendo `(solicitante_tipo_contenido_id, solicitante_id_objeto)` para que `HasEntityScope` limite por entidad.
- **T5.3** Catálogos: lectura para cualquier autenticado; escritura denegada (solo lectura).
- **T5.4** Acciones de flujo restringidas por rol (p. ej. evaluación técnica → grupo `DIGEP`; opinión jurídica → `OGAJ`; opinión CONAPRES → `CONAPRES`; publicación/firma → `Secretaría General`). Definir clases de permiso por rol reutilizando los grupos seedeados.

**Criterio:** cada acción de flujo valida el rol correspondiente; el alcance institucional aplica a `Convention`.

---

## T6 — Filters (`apps/convenios/filters.py`)

- **T6.1** `ConventionFilter`: por `tipo_convenio`, `estado_actual`, `convenio_marco`, rango de `fecha_solicitud`/`fecha_inicio`/`fecha_fin`, `solicitante` (tipo+id).
- **T6.2** Filtros para `ClinicalField` (por `ipress`, `carrera_profesional`, `especialidad`, `ambito_geografico_sanitario`) y para entidades principales (por `region`, `activo`, etc.).
- **T6.3** `OrderingFilter`/`SearchFilter` donde aplique (búsqueda por `titulo`/`codigo` en convenios).

**Criterio:** los listados clave soportan los filtros del RF-CV-26 (tipo, estado, universidad, región, sede, vigencia, entidad).

---

## T7 — URLs / router (`apps/convenios/urls.py` + registro en `config/api_urls.py`)

- **T7.1** `DefaultRouter` del módulo registrando todos los ViewSets con **basenames en inglés** (p. ej. `conventions`, `convention-templates`, `clinical-fields`, `technical-evaluations`, `conapres-opinions`, `legal-opinions`, `signatures`, `publications`, `regional-governments`, `regional-organs`, `executing-units`, `ipress`, `minsa-organs`, `conapres`, `representatives`, `universities`, `university-authorities`, `faculties`, `professional-careers`, `university-campuses`, `documents`, y catálogos como `regions`, `specialties`, etc.).
- **T7.2** En `config/api_urls.py`, extender el router raíz con el router de `convenios` (todo bajo `/api/v1/`).
- **T7.3** Verificar que el esquema OpenAPI (`/api/schema/`) incluya los nuevos paths.

**Criterio:** `manage.py check` limpio; `spectacular` genera sin error; los endpoints aparecen en el esquema.

---

## Referencias

- **Reglas de negocio (§6 del módulo 1):** RN-3 (Específico→Marco vigente) → T3.1; CONAPRES/campos clínicos solo Específico → T3.4/T3.5; no firmar con observaciones pendientes → T3.7; trazabilidad de estados → T3.2 + `ConventionStatusHistory`; versionado documental → T4.5/`Document`.
- **Requerimientos funcionales:** RF-CV-01..26 (registro, evaluación, opiniones, campos clínicos, firmas, publicación, vigencia, trazabilidad, reportes/consulta).
- **Schema:** tablas y columnas exactas en `docs/db_schema_modulo_01_convenios.md`. No inventar campos.
- **Auth/permisos base:** `apps/common/permissions.py`, `apps/common/selectors.py`.

## Fuera de alcance (este spec)
Testing automatizado; generación real de PDF/plantillas; integración del repositorio externo de archivos (solo se guarda `referencia_externa`); reportes/exportación.
