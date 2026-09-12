# Spec — Módulo `internados` (Registrar Internados)

Tareas exactas para `apps/internados/` según [arquitectura](../docs/arquitectura_desarrollo.md) y [schema M2](../docs/db_schema_modulo_02_internados.md). Producido por el agente **spec** (SDD). Patrón ya establecido en el módulo `convenios` (services/selectors, ViewSets delgados, JWT + alcance institucional, auditoría transversal, escritura de master-data solo `Administrador RENADS`).

## Resumen

Exponer vía DRF (bajo `/api/v1/`) los recursos del módulo: catálogos (solo lectura), `Student` y `Tutor` (CRUD), y el núcleo `Internship`/`Rotation` con su flujo y reglas de negocio. Reutiliza modelos del módulo 1 (`Convention`, `ClinicalField`, `Ipress`, `University`, `ConventionParticipant`).

**Convenciones:** clases inglés; campos/tablas/`help_text` español; endpoints inglés; docstrings español. Sin tests (fuera de alcance MVP). Reutilizar `apps/common` (permisos, auditoría) y el patrón `AuditedModelViewSet`.

**Entidades** (modelos en `apps/internados/models.py`):
- Catálogos: `InternshipStatus`, `RotationStatus`, `ServiceArea`, `IdentityDocumentType`, `RelationshipType` (tabla `parentesco`, parentesco del contacto de emergencia), `AcademicPeriod` (tabla `periodo_academico`), `AnnexDocument` (tabla `documentos_anexos`).
- Personas: `Student`, `Tutor`. `Student` incluye `nota_promedio_ponderado`, contacto de emergencia inline (`contacto_emergencia_nombre`, `contacto_emergencia_telefono`, `contacto_emergencia_parentesco` → `RelationshipType`) y las FKs nullable `periodo_academico` (→ `AcademicPeriod`) y `especialidad` (→ `convenios.Specialty`). `Tutor` incluye la relación **M2M `universidades`** (→ `convenios.University`) vía la tabla puente `TutorUniversity` (`tutor_universidad`), de **1 a 2** universidades (RN-24).
- Núcleo: `Internship`, `InternshipStatusHistory`, `TutorHistory`, `Rotation`, `RotationAuthorization`, `RotationStatusHistory`.

> **Feature F1 — Periodo académico, declaraciones juradas y RN-19 (2026-07):** ver el bloque **Feature F1** al final del spec. Introduce los catálogos `AcademicPeriod`/`AnnexDocument`, las FKs `periodo_academico`/`especialidad` en `Student`, el renombrado del código de nivel académico `CARRERA_PROFESIONAL` → `PREGRADO` (módulo 1) y la validación condicional **RN-19**. Amplía las tareas T1, T3, T4, T6 y T7.

> **Feature F2 — Adjunto real de anexos (declaraciones juradas) por estudiante (2026-07):** ver la tarea **T-F2.2** al final del spec. Agrega al `StudentViewSet` las acciones `annex-upload`/`annex-checklist` que adjuntan el PDF real de cada `AnnexDocument` de `tipo_actor = "INTERNO"` reutilizando el mixin transversal `AnnexAttachmentMixin` (definido en `apps/convenios/mixins.py`) y el backend de almacenamiento de `spec/almacenamiento.md` (Etapa 2). Con esto, el flujo de adjunto real por estudiante **deja de estar fuera de alcance**.

> **Feature F3 — Registro de internos por universidad, unicidad, onboarding del interno y estado de declaraciones juradas (2026-07):** ver el bloque **Feature F3** al final del spec. Introduce: (a) el registro de internos a cargo del **usuario de universidad** con **alcance por universidad** (1..N vía `perfil_usuario_entidad`); (b) la **unicidad de interno por DNI** (un internado vigente por estudiante) con **excepción de estados liberadores** (incl. `SUSPENDIDO`); (c) el **onboarding del interno** al asociarse: creación de un `User` (username = DNI, clave temporal, rol `Interno`, solo lectura de sus datos), **notificación por correo** (sede docente, fechas, tutor, instrucción de adjuntar DJ); y (d) el **estado de declaraciones juradas** `Internship.estado_declaraciones` (PENDIENTE/COMPLETAS/OBSERVADAS/VALIDADAS) con revisión humana. Amplía T3.1 y agrega el rol `Interno`.

> **Feature F4 — Universidades del tutor (2026-07):** ver la tarea **T-F4.1** al final del spec. Agrega la relación M2M `Tutor.universidades` (tabla puente `tutor_universidad`) con la regla de negocio **RN-24** (de 1 a 2 universidades por tutor), validada por `services.validar_universidades_tutor` desde `TutorSerializer`.

> **Feature F6 — Eliminar `anio_academico` de `estudiante` (refactor 2026-07):** ver el bloque **Feature F6** al final del spec. Elimina el campo `anio_academico` del modelo `Student` por ser **redundante** con `periodo_academico`; la columna del Excel de carga masiva pasa a **ignorarse**. Sincroniza modelo, migración, services, schema y frontend.

---

## Bloques sugeridos
- **Bloque 1 (núcleo + services):** selectors, services (todas las RN), serializers de `Internship`/`Rotation` + entradas de acciones, `InternshipViewSet`/`RotationViewSet` con acciones de flujo, permisos, filtros, router del núcleo.
- **Bloque 2 (catálogos + personas):** catálogos read-only, CRUD de `Student` y `Tutor`, filtros, registro en router.
- **Bloque F1 (feature 2026-07):** catálogos CRUD `AcademicPeriod`/`AnnexDocument`, FKs de `Student`, renombrado del código de nivel académico y validación **RN-19** (helper de services reutilizado por serializer y bulk-upload).
- **Bloque F2 (feature 2026-07):** adjunto real de anexos por estudiante (`StudentViewSet` + `AnnexAttachmentMixin`), dependiente de la Etapa 2 de `spec/almacenamiento.md`.
- **Bloque F3 (feature 2026-07):** registro de internos por universidad con alcance, unicidad por DNI (excepción `SUSPENDIDO`), onboarding del interno (usuario `Interno` + correo) y `estado_declaraciones`. Depende de F2 (checklist de DJ) y de `spec/almacenamiento.md` Etapa 2.
- **Bloque F5 (refactor 2026-07):** el **contacto de emergencia** se mueve de `estudiante` a `interno`, y el **adjunto real de anexos del actor `INTERNO`** se mueve de `StudentViewSet` a `InternshipViewSet` (`interns/{id}/annex-upload`/`annex-checklist`). Ver **T-F5.1**. Supersede la ubicación definida en F2 (T-F2.2).
- **Bloque F6 (refactor 2026-07):** eliminar el campo `anio_academico` de `estudiante` (modelo, migración a mano, carga masiva, schema y frontend). Ver **T-F6.1..T-F6.7**.

---

## T1 — Serializers (`apps/internados/serializers.py`)

- **T1.1** `InternshipReadSerializer` (anida estudiante, convenio, ipress, tutor, estado legibles) / `InternshipWriteSerializer` (FKs; `estado_actual`, `creado_por`, `fecha_fin` calculados/solo lectura si aplica).
- **T1.2** `RotationReadSerializer` / `RotationWriteSerializer` (`interno` se toma de la URL en acciones anidadas; `estado_actual`, `numero_rotacion`, `creado_por` solo lectura — los fija el service).
- **T1.3** Entradas de acciones: `CambiarEstadoInternadoSerializer` (estado_codigo, observacion), `CambiarTutorSerializer` (tutor, fecha_cambio, motivo), `RotationAuthorizationSerializer` (participante_convenio, resultado, fecha_autorizacion, observaciones).
- **T1.4** Historiales: serializers de `InternshipStatusHistory`, `TutorHistory`, `RotationStatusHistory`.
- **T1.5** `Student` y `Tutor`: `ModelSerializer` (CRUD; `Student` expone `nota_promedio_ponderado` y los 3 campos de contacto de emergencia). Catálogos: serializers de solo lectura (incluye `parentesco`/`relationship-types`).
- **T1.6 (F1)** `StudentSerializer`: exponer las nuevas FKs `periodo_academico` y `especialidad` (quedan en `fields = "__all__"`; ambas opcionales a nivel de campo). Implementar `StudentSerializer.validate(self, attrs)` que:
  - Fusione `attrs` con `self.instance` en updates parciales (tomar `carrera_profesional`, `periodo_academico`, `especialidad` del `instance` cuando no vengan en `attrs`).
  - Invoque el helper `services.validar_regla_periodo_especialidad(...)` (**RN-19**, ver T3.10) y traduzca cualquier fallo a `serializers.ValidationError` con mensajes en español apuntando al campo faltante/sobrante.
  - No incluir aquí la lógica de la regla: solo delegar en el helper (fuente única de verdad compartida con el bulk-upload).

**Criterio:** `Internship` y `Rotation` tienen read/write; campos controlados por services marcados `read_only`. **(F1)** crear estudiante PREGRADO sin `periodo_academico` → 400; crear estudiante PREGRADO con `especialidad` → 400; crear estudiante de otro nivel sin `especialidad` → 400; con `periodo_academico` en otro nivel → 400.

---

## T2 — Selectors (`apps/internados/selectors.py`)

- **T2.1** `internados_visibles(usuario)`: queryset de `Internship` filtrado por alcance institucional (la universidad del estudiante dentro de las entidades del usuario; superusuario ve todo; sin perfiles → ninguno). Reutilizar `apps/common/selectors`.
- **T2.2** `rotaciones_de(internado)`, `historial_internado(internado)`, `historial_rotacion(rotacion)`, `historial_tutor(internado)`.
- **T2.3** `rotaciones_count(internado)` (para RN-9).

**Criterio:** las vistas usan selectors; el alcance institucional se aplica en `internados_visibles`.

---

## T3 — Services (`apps/internados/services.py`)

Toda escritura en `transaction.atomic()`, con auditoría (`apps.common.services.registrar_auditoria`) y, en cambios de estado, registro en el historial correspondiente.

- **T3.1** `crear_internado(datos, usuario)`:
  - **RN-2/3/4:** `convenio` debe ser **Específico** y estar vigente (estado en {`VIGENTE`,`PUBLICADO`,`SUSCRITO`}); no se permite sobre Marco.
  - **RN-5:** `tutor` obligatorio (el modelo ya lo exige).
  - **RN-6:** `fecha_fin - fecha_inicio ≤ 1 año`.
  - **RN-13/17:** el `campo_clinico` pertenece al convenio y no excede su `cantidad_maxima` (disponibilidad = `cantidad_maxima` − internos asignados); la **universidad** asigna a los campos clínicos disponibles por sede/carrera del Convenio Específico.
  - Coherencia de ámbito: `ambito_geografico_sanitario` consistente con el `campo_clinico`/`ipress`.
  - Estado inicial `REGISTRADO`; `creado_por = usuario`.
  - **(F3) Acceso por universidad (RN-20):** el registro lo efectúa el **usuario de universidad**; `exigir_ambito(usuario, ContentType(University), universidad_del_estudiante_id)` — rechaza si la universidad del estudiante está fuera de su alcance institucional (`perfil_usuario_entidad`). Un usuario puede tener acceso a **varias** universidades (varios perfiles); superusuario y `Administrador RENADS` exentos. Ver **T-F3.1**.
  - **(F3) Unicidad de interno por DNI (RN-21):** rechazar si el estudiante ya tiene un `Internship` en **estado bloqueante**. Estados **liberadores** que **sí** permiten una nueva asignación: `SUSPENDIDO`, `RETIRADO`, `CULMINADO`, `ANULADO`. Estados **bloqueantes**: `REGISTRADO`, `PENDIENTE_VALIDACION`, `OBSERVADO`, `VALIDADO`, `ACTIVO`, `EN_ROTACION_*`. (El estudiante es único por documento a nivel DB; esta regla controla el internado vigente.) Ver **T-F3.2**.
  - **(F3) Onboarding del interno (RN-22):** en la misma transacción, tras crear el internado, invocar `services.aprovisionar_interno(internado, usuario)` → crea `User` (username = número de DNI, clave temporal aleatoria, `debe_cambiar_password=True`, grupo `Interno`, `perfil_usuario_entidad` sobre la entidad `Student`), inicializa `estado_declaraciones = PENDIENTE`, y **notifica por correo** (best-effort, post-commit). Ver **T-F3.3**/**T-F3.4**/**T-F3.5**.
- **T3.2** `cambiar_estado_internado(internado, nuevo_estado_codigo, usuario, observacion="")`.
- **T3.3** `cambiar_tutor(internado, datos, usuario)` (**RN-14**): registra `TutorHistory` (tutor, fecha_cambio, motivo, responsable=usuario) y actualiza `internado.tutor`.
- **T3.4** `crear_rotacion(internado, datos, usuario)`:
  - **RN-8:** `ipress_origen` e `ipress_destino` deben pertenecer al mismo `ambito_geografico_sanitario` del internado.
  - **RN-9:** el estudiante no supera **4** rotaciones (asignar `numero_rotacion` = actuales + 1; rechazar si > 4).
  - **RN-12:** `fecha_inicio`/`fecha_fin` dentro del periodo del internado.
  - Estado inicial `SOLICITADA`.
- **T3.5** `autorizar_rotacion(rotacion, datos, usuario)` (**RN-10**): el `participante_convenio` debe ser **firmante** (`es_firmante=True`) del Convenio Específico del internado; crea `RotationAuthorization`; estado `AUTORIZADA`/`OBSERVADA`/`RECHAZADA` según `resultado`.
- **T3.6** `iniciar_rotacion(rotacion, usuario)` (**RN-11**): bloquea si no existe autorización `APROBADO`; pasa a `EN_CURSO`.
- **T3.7** `cambiar_estado_rotacion(rotacion, nuevo_estado_codigo, usuario, observacion="")`.
- **T3.8** `registrar_estudiantes_masivo(archivo_excel, usuario)` (**RN-16**): parsea el `.xlsx` (estructura de §6 bis del schema M2, alineada con la trama oficial `TramaCargaEstudiante.xlsx`), valida por fila (unicidad `tipo_documento`+`numero_documento`, catálogos/entidades resueltos por id **o** `codigo`, alcance institucional de `universidad`), crea en lote dentro de `transaction.atomic()` con auditoría por fila y devuelve **resumen** `{creados, omitidos, errores:[{fila, motivo}]}`. Las filas inválidas no abortan el lote. Los encabezados de la trama llevan sufijo `_id` (`tipo_documento_identidad_id`, `universidad_id`, `carrera_profesional_id`, `periodo_academico_id`, `especialidad_id`, `ubigeo_id`) y se mapean a la clave canónica interna vía `CARGA_ALIAS_COLUMNAS` (se aceptan también los nombres históricos sin sufijo).
  - **(F1)** resolver por `codigo` las columnas opcionales `periodo_academico` (→ `AcademicPeriod.codigo`) y `especialidad` (→ `convenios.Specialty.codigo`), y aplicar **RN-19** por fila invocando `validar_regla_periodo_especialidad(...)` (T3.10). Una fila que viole RN-19 se reporta en `errores` con `{fila, motivo}` y **no** aborta el lote.
  - **(F6)** la columna `anio_academico` de la trama, si viene, se **ignora** (no se lee ni valida); no es requerida ni opcional-mapeada. Ver **T-F6.3**.
- **T3.9** Prelación (**RN-18**): al asignar cupos de un `campo_clinico`, ordenar candidatos por `estudiante.nota_promedio_ponderado` **descendente** (orden de mérito); respetar disponibilidad (**RN-17**).
- **T3.10 (F1)** `validar_regla_periodo_especialidad(*, carrera_profesional, periodo_academico, especialidad)` (**RN-19**) — helper puro y reutilizable, **fuente única de verdad** de la regla:
  - Deriva `nivel = carrera_profesional.nivel_academico.codigo` (usar `select_related` al cargar el estudiante para evitar N+1 en bulk).
  - Si `nivel == "PREGRADO"`: `periodo_academico` **requerido** y `especialidad` **debe ser nula**.
  - Para cualquier otro nivel (`SEGUNDA_ESPECIALIDAD`/`MAESTRIA`/`DOCTORADO`/…): `especialidad` **requerida** y `periodo_academico` **debe ser nula**.
  - Ante incumplimiento, lanzar un error con mensaje en español identificando el campo (p. ej. "El periodo académico es obligatorio para estudiantes de Pregrado." / "La especialidad no aplica a estudiantes de Pregrado."). El helper puede lanzar `django.core.exceptions.ValidationError`; el serializer (T1.6) lo re-mapea a `serializers.ValidationError`; el bulk-upload (T3.8) lo captura y lo vuelca en `errores`.
  - Sin acceso a `request` ni a DRF: solo recibe los objetos ya resueltos (o `None`).

**Criterio:** cada RN del §6 del módulo está cubierta por un service; ningún cambio de estado fuera de services; auditoría e historial siempre registrados. **(F1)** la regla **RN-19** vive en un único helper de `services.py` y es invocada tanto por `StudentSerializer.validate()` como por `registrar_estudiantes_masivo`.

---

## T4 — ViewSets (`apps/internados/views.py`)

- **T4.1** Catálogos: `ReadOnlyModelViewSet` (reutilizar factory equivalente).
- **T4.2** `StudentViewSet`, `TutorViewSet`: CRUD con auditoría (`AuditedModelViewSet`). Escritura por rol `Universidad`/`Administrador RENADS` (o `IsAdminRoleOrReadOnly` según política).
  - Acción **`bulk-upload`** (`POST /students/bulk-upload/`, multipart con `archivo` `.xlsx`, rol `Universidad`/`Administrador RENADS`): delega en `services.registrar_estudiantes_masivo`; responde con el resumen de la carga (**RN-16**). Requiere `openpyxl` (o equivalente) para leer el Excel.
  - **(F1)** `StudentViewSet.filterset_fields`: agregar `periodo_academico` y `especialidad` a la lista existente (`["universidad", "carrera_profesional", "numero_documento", "activo"]`).
  - **(F2)** `StudentViewSet` incorpora el mixin transversal `AnnexAttachmentMixin` con `annex_actor = "INTERNO"` (acciones `annex-upload`/`annex-checklist`). Detalle en **T-F2.2**.
- **T4.3** `InternshipViewSet` (`ModelViewSet`): `get_queryset = selectors.internados_visibles`; create/update vía services; acciones: `cambiar-estado`, `cambiar-tutor`, `historial`, `rotaciones` (GET lista / POST crea rotación).
- **T4.4** `RotationViewSet` (`ModelViewSet`): acciones `autorizar`, `iniciar`, `cambiar-estado`, `historial`. Escritura vía services.
- **T4.5 (F1)** Catálogos CRUD nuevos vía factory `_entity_viewset` de `apps.convenios.views` (escritura solo `Administrador RENADS`, lectura autenticados). Definir en `apps/internados/views.py` un diccionario **`ENTITY_VIEWSETS`** (análogo a `CATALOG_VIEWSETS`):
  - `"academic-periods": _entity_viewset(im.AcademicPeriod, filterset_fields=["activo"], search_fields=["codigo", "nombre"])`.
  - `"annex-documents": _entity_viewset(im.AnnexDocument, filterset_fields=["tipo_actor", "obligatorio", "activo"], search_fields=["codigo", "nombre"])` **(F2)**.
  - Importar `_entity_viewset` desde `apps.convenios.views` (junto al ya importado `_catalog_viewset`).

**Criterio:** ViewSets delgados; escritura vía services; lectura vía selectors; serializer read/write por acción. **(F1)** `StudentViewSet` filtra por `periodo_academico` y `especialidad`; `academic-periods` y `annex-documents` son CRUD con escritura restringida a `Administrador RENADS` y lectura para autenticados.

---

## T5 — Permissions (`apps/internados/permissions.py`)

- **T5.1** Global `IsAuthenticated` + `IsInstitutionalMember`.
- **T5.2** Alcance de objeto sobre `Internship`/`Rotation` por la universidad del estudiante (clase tipo `InternshipScope`, análoga a `ConventionScope`).
- **T5.3** Acciones por rol: `cambiar-tutor`/registrar estudiante → `Universidad`; `autorizar` rotación → `Autoridad de convenio`; transiciones administrativas → `Administrador RENADS`. Reutilizar helper `exigir_roles`.

**Criterio:** autorización de rotación restringida a autoridad suscrita (rol + RN-10); alcance institucional aplicado.

---

## T6 — Filters (`apps/internados/filters.py`)

- **T6.1** `InternshipFilter`: por `convenio`, `ipress`, `tutor`, `estado_actual`, `ambito_geografico_sanitario`, rango de `fecha_inicio`/`fecha_fin`; búsqueda por estudiante (documento/nombre).
- **T6.2** `RotationFilter`: por `interno`, `estado_actual`, `ipress_origen`/`ipress_destino`, `servicio_area`.
- **T6.3** `StudentFilter`: por `universidad`, `carrera_profesional`, `numero_documento`.
  - **(F1)** agregar `periodo_academico` y `especialidad`. Si `Student` se filtra por `filterset_fields` en la vista (ver T4.2) en lugar de por una clase `StudentFilter`, agregar ambos campos allí; mantener una sola fuente para no duplicar.

**Criterio:** consultas RF-IN-23 (por convenio, universidad, sede, tutor, región, periodo) soportadas. **(F1)** `GET /api/v1/students/?periodo_academico=<id>` y `?especialidad=<id>` filtran correctamente.

---

## T7 — URLs / router (`apps/internados/urls.py` + registro en `config/api_urls.py`)

- **T7.1** `DefaultRouter` con basenames en inglés: `students` (incluye la acción `bulk-upload`), `tutors`, `interns` (recurso Internship, tabla `interno`), `rotations`, y catálogos (`internship-statuses`, `rotation-statuses`, `service-areas`, `identity-document-types`, `relationship-types`).
- **T7.2** Incluir el router de `internados` en `config/api_urls.py` (bajo `/api/v1/`).
- **T7.3** Verificar OpenAPI incluye los nuevos paths.
- **T7.4 (F1)** En `apps/internados/urls.py`, tras el loop de `CATALOG_VIEWSETS`, agregar un loop análogo sobre `views.ENTITY_VIEWSETS` (T4.5) que registre `academic-periods` y `annex-documents` con su `basename` respectivo. No tocar los registros existentes.

**Criterio:** `manage.py check` limpio; `spectacular` sin error; endpoints en el esquema. **(F1)** los paths `/api/v1/academic-periods/` y `/api/v1/annex-documents/` aparecen en OpenAPI con sus operaciones CRUD.

---

## Feature F1 — Periodo académico, declaraciones juradas y RN-19 (2026-07)

Feature del módulo Internados que agrega periodos académicos, el catálogo maestro de declaraciones juradas (anexos) y la regla condicional **RN-19** que decide entre `periodo_academico` y `especialidad` según el nivel académico del estudiante. Incluye un cambio puntual en el módulo 1 (`apps/convenios`): renombrar el código de nivel académico `CARRERA_PROFESIONAL` → `PREGRADO`.

### T-F1.1 — Renombrar el código de nivel académico (módulo 1, `apps/convenios`)
- En el catálogo `AcademicLevel` (tabla `nivel_academico`), renombrar el registro con `codigo = "CARRERA_PROFESIONAL"` a `codigo = "PREGRADO"`, `nombre = "Pregrado"`.
- Actualizar la constante `ACADEMIC_LEVELS` del seed `apps/convenios/migrations/0002_seed_catalogos.py` (entrada `("CARRERA_PROFESIONAL", "Carrera profesional")` → `("PREGRADO", "Pregrado")`) y crear una **migración de datos** que actualice el registro existente por `codigo` (idempotente; sin borrar la fila para no romper FKs de `ProfessionalCareer`).
- Buscar y actualizar cualquier referencia literal a `"CARRERA_PROFESIONAL"` en código (services/serializers/tests-de-datos) por `"PREGRADO"`. La constante `"PREGRADO"` usada por RN-19 (T3.10) debe coincidir exactamente con el `codigo` resultante.
- **Criterio:** no queda ninguna referencia a `CARRERA_PROFESIONAL`; `manage.py migrate` deja el registro con `codigo="PREGRADO"`; `manage.py check` limpio.

### T-F1.2 — Modelo `AcademicPeriod` (`apps/internados/models.py`)
- Nueva clase `AcademicPeriod(Catalog)` (hereda `codigo`/`nombre`/`activo` de `apps.convenios.models.Catalog`), `Meta.db_table = "periodo_academico"`, `verbose_name = "periodo académico"`. Sin campos extra. Ejemplo de datos: `codigo="2026-I"`, `nombre="2026-I"`.
- Migración `makemigrations internados`.
- **Criterio:** tabla `periodo_academico` creada; `manage.py check` limpio; documentado en `docs/db_schema_modulo_02_internados.md`.

### T-F1.3 — Modelo `AnnexDocument` (`apps/internados/models.py`)
- Nueva clase `AnnexDocument(Catalog)` con:
  - `descripcion = models.TextField("descripción", blank=True, help_text="Descripción de la declaración jurada / anexo")`.
  - `obligatorio = models.BooleanField("obligatorio", default=True, help_text="Indica si el anexo es de presentación obligatoria")`.
  - `Meta.db_table = "documentos_anexos"`, `verbose_name = "documento anexo"`.
- Es el **catálogo maestro** (lista de descripciones) de las **declaraciones juradas** que el estudiante debe adjuntar tras registrarse como interno. El **flujo de adjunto real** del PDF por estudiante se cubre en **T-F2.2** (feature F2). Este bloque F1 solo cubre el catálogo maestro y su CRUD.
- Migración `makemigrations internados`.
- **Criterio:** tabla `documentos_anexos` con `descripcion` y `obligatorio`; `manage.py check` limpio; documentado en el schema M2.

### T-F2.1 — `tipo_actor` en `AnnexDocument` (documentos por actor) (`apps/internados/models.py`)
- Generaliza el catálogo: además del interno, otros actores adjuntan documentos (**resolución del cargo** y **documento de identidad**).
- Agregar `tipo_actor = models.CharField("tipo de actor", max_length=30, choices=ANNEX_ACTOR, default="INTERNO", help_text="Actor que debe presentar el documento")` con `ANNEX_ACTOR = [("INTERNO", …), ("AUTORIDAD_UNIVERSIDAD", …), ("REPRESENTANTE", …)]`. Las autoridades de **CONAPRES** caen bajo `REPRESENTANTE` (tabla `representante` polimórfica).
- Endpoint `annex-documents` (`views.ENTITY_VIEWSETS`): agregar `tipo_actor` a `filterset_fields`.
- Migraciones a mano: `0010_annexdocument_tipo_actor` (AddField, default `INTERNO`) y `0011_seed_documentos_actor` (seed `RESOL_AUTUNI`/`DNI_AUTUNI` para `AUTORIDAD_UNIVERSIDAD`, `RESOL_REP`/`DNI_REP` para `REPRESENTANTE`, todos `obligatorio=True`).
- El **adjunto real por entidad** (PDF por `AnnexDocument` según `tipo_actor`) se cubre en **T-F2.2** (estudiante) y en `spec/almacenamiento.md` Etapa 2 (autoridad de universidad y representante). Este bloque solo agrega la columna `tipo_actor` y el seed.
- **Criterio:** `manage.py check` limpio; `spectacular` sin error; `/api/v1/annex-documents/?tipo_actor=` filtra; seed con {`INTERNO`:4, `AUTORIDAD_UNIVERSIDAD`:2, `REPRESENTANTE`:2}; docs M2 + ER global + html + CLAUDE.md sincronizados.

### T-F2.2 — Adjunto real de anexos por estudiante en `StudentViewSet` (`apps/internados/views.py`)

> **⚠ Superado por F5 (T-F5.1):** el adjunto del actor `INTERNO` se movió al **internado**
> (`InternshipViewSet`, `interns/{id}/annex-upload`/`annex-checklist`). El `StudentViewSet` ya
> **no** expone estas acciones. La descripción histórica abajo se conserva por trazabilidad;
> léase «`interns/{id}`» y «`Internship`» donde diga «`students/{id}`» y «estudiante».

Depende de **`spec/almacenamiento.md` — Etapa 2** (mixin `AnnexAttachmentMixin`, serializer `AnnexUploadSerializer`, FK `Document.documento_anexo`, `adjuntar_documento(..., documento_anexo=...)` y seed `DocumentType ANEXO`), que son transversales y viven en `apps/convenios`. Aquí solo se **aplica** el mixin al `StudentViewSet` para el actor `INTERNO`.

- **T-F2.2.1** Agregar `AnnexAttachmentMixin` (import desde `apps.convenios.mixins`) a las bases de `StudentViewSet`, fijando el atributo de clase `annex_actor = "INTERNO"`. No alterar el CRUD ni la acción `bulk-upload` ya existentes; el mixin solo aporta dos acciones nuevas.
- **T-F2.2.2** Acción **`POST /api/v1/students/{id}/annex-upload/`** (multipart, provista por el mixin):
  - Cuerpo: `{documento_anexo, archivo, nombre_archivo?}`; `archivo` **solo PDF** (validado por `AnnexUploadSerializer`).
  - Enforcement: el `documento_anexo` debe estar activo y su `tipo_actor` ser `"INTERNO"`; en caso contrario **400** en español.
  - Sube el binario vía el backend seleccionado por settings y llama `adjuntar_documento(estudiante, tipo_documento=<ANEXO>, referencia_externa=<key>, usuario=request.user, documento_anexo=<anexo>)` (versionado por `(estudiante, documento_anexo)` + auditoría — RNF-DOC-04 / RNF-AUD-01).
  - Respuesta **201** con el `Document` creado (`DocumentSerializer`).
- **T-F2.2.3** Acción **`GET /api/v1/students/{id}/annex-checklist/`** (provista por el mixin): lista los `AnnexDocument` activos de `tipo_actor="INTERNO"` con `adjuntado`/`documento_id`/`version`/`referencia_externa` de la versión `ACTIVO` de ese estudiante; base del checklist requeridos (`obligatorio=True`) vs. adjuntados.
- **T-F2.2.4** Permisos: heredan los del `StudentViewSet` (`[IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]`). `annex-upload` es escritura ⇒ rol `Universidad`/`Administrador RENADS` y alcance por la universidad del estudiante; `annex-checklist` es lectura para autenticados con alcance. No relajar permisos.
- **T-F2.2.5** `@extend_schema` en ambas acciones (lo aporta el mixin) para que aparezcan en OpenAPI/Swagger.

- **Criterio:** `POST /api/v1/students/{id}/annex-upload/` con un anexo de `tipo_actor="INTERNO"` y un PDF → 201 y `Document` versionado por `documento_anexo`; con un anexo de otro `tipo_actor` → 400; con un archivo no PDF → 400; re-subir el mismo anexo del mismo estudiante crea `version=2` y marca la anterior `REEMPLAZADO`; `GET .../annex-checklist/` devuelve todos los anexos `INTERNO` activos con su estado `adjuntado`; ambas acciones aparecen en OpenAPI; un usuario sin rol/alcance recibe 403.

### T-F1.4 — FKs nuevas en `Student` (`apps/internados/models.py`)
- Agregar a `Student`:
  - `periodo_academico = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, db_column="periodo_academico_id", null=True, blank=True, related_name="+", help_text="Periodo académico (obligatorio para Pregrado — RN-19)")`.
  - **Re-agregar** `especialidad = models.ForeignKey("convenios.Specialty", on_delete=models.SET_NULL, db_column="especialidad_id", null=True, blank=True, related_name="+", help_text="Especialidad (obligatoria para niveles distintos de Pregrado — RN-19)")` (importar `Specialty` ya disponible en el módulo).
- Ambas `null=True, blank=True`: la obligatoriedad condicional la aplica **RN-19** a nivel de aplicación (T3.10), no la BD.
- Migración `makemigrations internados`.
- **Criterio:** columnas `periodo_academico_id` (PROTECT) y `especialidad_id` (SET_NULL) creadas; `manage.py check` limpio; schema M2 actualizado.

### T-F1.5 — RN-19: helper de services + integración
- Implementar `services.validar_regla_periodo_especialidad(...)` (ver **T3.10**).
- Integrar en `StudentSerializer.validate()` (ver **T1.6**), fusionando `self.instance` en updates parciales.
- Integrar en `registrar_estudiantes_masivo` por fila (ver **T3.8**), reportando la violación en `errores` sin abortar el lote.
- **Criterio:** una sola implementación de la regla en `services.py`; el serializer y el bulk-upload la comparten; comportamiento verificable por 400 (individual) y por entrada en `errores` (bulk).

### T-F1.6 — CRUD y router de los nuevos catálogos
- ViewSets vía `ENTITY_VIEWSETS` (ver **T4.5**) y registro en el router (ver **T7.4**): endpoints `academic-periods` y `annex-documents` bajo `/api/v1/`.
- **Criterio:** CRUD funcional; escritura solo `Administrador RENADS`, lectura para autenticados; ambos paths en OpenAPI.

### Criterios de aceptación transversales de F1
- `python manage.py check` limpio y `python manage.py makemigrations --check` sin cambios pendientes tras aplicar las migraciones.
- Crear un estudiante con carrera de nivel `PREGRADO` **sin** `periodo_academico` → **400**; con `especialidad` → **400**.
- Crear un estudiante con carrera de nivel distinto de `PREGRADO` **sin** `especialidad` → **400**; con `periodo_academico` → **400**.
- Bulk-upload con una fila que viole RN-19 → esa fila en `errores` (`{fila, motivo}`), el resto se crea.
- `GET /api/v1/students/?periodo_academico=<id>` y `?especialidad=<id>` filtran.
- Endpoints `/api/v1/academic-periods/` y `/api/v1/annex-documents/` presentes en el esquema OpenAPI (spectacular sin error).
- No queda ninguna referencia al código `CARRERA_PROFESIONAL` en el repositorio.
- Convenciones RENADS respetadas: clases en inglés (`AcademicPeriod`, `AnnexDocument`), endpoints en inglés (`academic-periods`, `annex-documents`), `db_table`/columnas/`help_text`/docstrings/`.md` en español.

---

## Feature F3 — Registro por universidad, unicidad, onboarding del interno y estado de declaraciones juradas (2026-07)

> Depende de **F2** (checklist de DJ del estudiante, T-F2.2) y de `spec/almacenamiento.md` Etapa 2 (backend de almacenamiento). Todo cambio de estado registra `historial_estado_internado` + `registrar_auditoria`.

### T-F3.1 — Registro de internos por usuario de universidad con alcance (RN-20)
- **Rol/grupo `Universidad`** (grupo Django). El acceso a 1..N universidades = 1..N filas en `perfil_usuario_entidad` con entidad `University` (no requiere modelo nuevo).
- `crear_internado` (T3.1): antes de crear, `exigir_ambito(usuario, ContentType.objects.get_for_model(University).id, universidad_del_estudiante.id)`. La universidad del estudiante se deriva de `estudiante.universidad`. Superusuario y `Administrador RENADS` exentos (ya contemplado en `exigir_ambito`).
- **Lectura con alcance:** `internados_visibles(usuario)` (T2.1) ya filtra por la universidad del estudiante dentro de las entidades del usuario; confirmar que `StudentViewSet.get_queryset` y `InternshipViewSet.get_queryset` respetan el alcance (universidad ∈ `entidades_del_usuario`).
- **Criterio:** un usuario `Universidad` con perfil sobre la universidad A puede registrar/ver internos de A; intento sobre la universidad B (sin perfil) → **403**; con perfiles A y B → ambas permitidas.

### T-F3.2 — Unicidad de interno por DNI con estados liberadores (RN-21)
- Helper de services `services.tiene_internado_vigente(estudiante) -> bool`: existe algún `Internship` del estudiante cuyo `estado_actual.codigo` ∈ **BLOQUEANTES** = {`REGISTRADO`, `PENDIENTE_VALIDACION`, `OBSERVADO`, `VALIDADO`, `ACTIVO`, `EN_ROTACION_SOLICITADA`, `EN_ROTACION_AUTORIZADA`, `EN_ROTACION_OBSERVADA`}.
- Estados **LIBERADORES** (no bloquean nueva asignación): {`SUSPENDIDO`, `RETIRADO`, `CULMINADO`, `ANULADO`}.
- `crear_internado` rechaza con **400** (mensaje español) si `tiene_internado_vigente(estudiante)`.
- **Criterio:** registrar un segundo internado para un estudiante con internado `ACTIVO` → 400; si su único internado previo está `SUSPENDIDO` (o `RETIRADO`/`CULMINADO`/`ANULADO`) → se permite el nuevo registro.

### T-F3.3 — Rol `Interno` y aprovisionamiento de usuario (RN-22)
- **Grupo `Interno`** (grupo Django) con acceso de **solo lectura a sus propios datos** (sin edición) + obligación de adjuntar sus DJ. Permisos: puede `GET` su propio `Student` y usar `annex-checklist`/`annex-upload` de su internado; **no** puede editar datos personales ni acceder a otros estudiantes/internados.
- Service `services.aprovisionar_interno(internado, usuario) -> User` (dentro de la transacción de `crear_internado`):
  - Crea/recupera `User`: `username = estudiante.numero_documento`; si ya existe el usuario (reingreso tras estado liberador), reutilizarlo. Contraseña **temporal aleatoria** (`get_user_model().objects.make_random_password()` o `secrets`), `set_password`.
  - Marca **cambio obligatorio de contraseña**: campo `debe_cambiar_password=True` en el modelo de usuario / perfil (definir el mecanismo mínimo; ver **Decisión de auth** abajo).
  - Asigna el grupo `Interno` y crea `perfil_usuario_entidad` (`entidad = estudiante` [`Student`], `grupo = Interno`, `activo=True`) idempotente (`get_or_create`).
  - Devuelve el `User`; `crear_internado` inicializa `internado.estado_declaraciones = "PENDIENTE"`.
- **Decisión de auth (mínima):** el forzado de cambio de clave se implementa con un flag booleano consultable por el front (claim en el JWT y/o campo en `/api/v1/me/`); el bloqueo efectivo de endpoints hasta el cambio queda como refuerzo del front en el MVP (el backend expone el flag y el endpoint de cambio de clave). No se implementa expiración de clave temporal en esta etapa.
- **Criterio:** al crear el internado se crea el usuario con username=DNI, grupo `Interno`, perfil sobre su `Student`, `debe_cambiar_password=True`; el interno autenticado ve sus datos (read-only) y su checklist, y no puede editar ni ver otros.

### T-F3.4 — Notificación por correo al interno
- `EMAIL_BACKEND`: **consola** en `dev` (`django.core.mail.backends.console.EmailBackend`), **SMTP** en `prod` vía `.env` (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`). Definir en `config/settings/{base,dev,prod}.py` con `python-decouple`.
- Service `services.notificar_registro_interno(internado)`: envía correo al `estudiante` (requiere email del estudiante; si falta, se omite y se registra aviso). Contenido (español): confirmación de registro como interno, **sede docente** (IPRESS/`campo_clinico`), **fecha de inicio y fin** del internado, **datos del tutor**, e instrucción de **adjuntar sus declaraciones juradas** en el sistema (link al checklist). Enví­o **best-effort** con `transaction.on_commit(...)` — un fallo de correo no revierte el registro.
- **Criterio:** en `dev` el correo aparece en el log de consola con los datos correctos; un fallo de envío no aborta `crear_internado`.

### T-F3.5 — `Internship.estado_declaraciones` (estado de las DJ) + transiciones
- Nuevo campo `estado_declaraciones = models.CharField(max_length=20, choices=ANNEX_STATUS, default="PENDIENTE")` en `Internship` (independiente de `estado_actual`). `ANNEX_STATUS = [("PENDIENTE",…),("COMPLETAS",…),("OBSERVADAS",…),("VALIDADAS",…)]`.
- **Transiciones:**
  - `PENDIENTE → COMPLETAS`: **automático**. Tras cada `annex-upload` (T-F2.2), recalcular: si todas las `AnnexDocument` `tipo_actor="INTERNO"` `obligatorio=True` tienen una versión `ACTIVO` adjunta para ese internado ⇒ `COMPLETAS`.
  - `COMPLETAS → VALIDADAS` / `COMPLETAS → OBSERVADAS`: paso de **revisión** por rol `Universidad`/`Administrador RENADS` (acción `POST /api/v1/interns/{id}/revisar-declaraciones/` con `{resultado: VALIDADAS|OBSERVADAS, observacion}`).
  - `OBSERVADAS → COMPLETAS`: al re-adjuntar y volver a cumplir el checklist.
- **Gate (RN-23):** `estado_actual` no puede pasar a **`ACTIVO`** salvo que `estado_declaraciones == "VALIDADAS"` (validar en `cambiar_estado_internado`).
- Service `services.recalcular_estado_declaraciones(internado)` (fuente única, invocado desde `annex-upload`); service `revisar_declaraciones(internado, resultado, usuario, observacion="")`.
- Cada transición registra historial + auditoría; `@extend_schema` en la acción de revisión.
- **Criterio:** internado nuevo → `PENDIENTE`; al completar las DJ obligatorias → `COMPLETAS` automático; revisión `OBSERVADAS` y re-adjunto → `COMPLETAS`; `VALIDADAS` habilita el paso a `ACTIVO`; intento de `ACTIVO` sin `VALIDADAS` → 400.

### Migraciones F3
- `apps/internados`: `AddField Internship.estado_declaraciones` (default `PENDIENTE`). Seed idempotente de los grupos `Universidad` e `Interno` (RunPython, `Group.objects.get_or_create`).
- El mecanismo de `debe_cambiar_password` según la **Decisión de auth** (flag en el modelo de usuario/perfil) con su migración correspondiente.

### Documentación F3
- `docs/db_schema_modulo_02_internados.md`: columna `internship.estado_declaraciones` + valores; nota RN-20/21/22/23. `docs/db_schema.html` y ER global si aplica. `CLAUDE.md`: nuevas reglas del módulo (registro por universidad, unicidad+excepción SUSPENDIDO, onboarding interno, estados DJ). `docs/api_almacenamiento_frontend.md` (de la Etapa 2): agregar el flag de cambio de clave y la acción `revisar-declaraciones`. Regenerar `docs/diccionario_datos.docx`.

### Criterios de aceptación transversales de F3
- `manage.py check` limpio; `makemigrations --check` sin pendientes; `spectacular` sin error; acción `revisar-declaraciones` en OpenAPI.
- RN-20 (403 fuera de alcance), RN-21 (400 con internado vigente; permitido tras estado liberador), RN-22 (usuario `Interno` creado con las restricciones), correo en consola (dev), RN-23 (gate de `ACTIVO`).
- Convenciones RENADS respetadas (clases inglés; endpoints inglés `revisar-declaraciones`; `db_table`/columnas/`help_text`/`.md` español).

---

## Feature F4 — Universidades del tutor (RN-24) (2026-07)

### T-F4.1 — Relación `Tutor.universidades` (1 a 2) (`apps/internados/`)
- **Modelo:** M2M `Tutor.universidades = ManyToManyField(convenios.University, through="TutorUniversity", related_name="tutores")`. Tabla puente `TutorUniversity` (`db_table="tutor_universidad"`): `tutor` (FK CASCADE, `db_column="tutor_id"`), `universidad` (FK PROTECT, `db_column="universidad_id"`), `unique_together=[("tutor","universidad")]`.
- **Regla RN-24 (1 a 2, sin repetidos):** helper único `services.validar_universidades_tutor(universidades)` (mensajes español). El tope `MAX_UNIVERSIDADES_TUTOR = 2` se valida a nivel de aplicación (no hay constraint DB de cardinalidad).
- **Serializer:** `TutorSerializer` expone `universidades` como lista de PKs **escribible** (`PrimaryKeyRelatedField(many=True)`); `validate_universidades` delega en el helper; `create`/`update` fijan la relación con `.set(...)`.
- **ViewSet:** `TutorViewSet` con `prefetch_related("universidades")` y `universidades` en `filterset_fields` (filtro `/api/v1/tutors/?universidades=<id>`). Permisos sin cambios (escritura `Universidad`/`Administrador RENADS`).
- **Migración a mano:** `0014_tutor_universidades` — `CreateModel TutorUniversity` + `AddField Tutor.universidades` (M2M through). Dependencias: `internados 0013` y `convenios 0011`.
- **Documentación:** `docs/db_schema_modulo_02_internados.md` (tabla `tutor`, nueva tabla `tutor_universidad`, RN-24), ER global, `db_schema.html`, `CLAUDE.md`, diccionario regenerado.
- **Criterio:** crear tutor con 0 universidades → 400; con 1 o 2 → OK; con 3 → 400; con repetidas → 400. `makemigrations --check` sin pendientes; `check` limpio; `spectacular` sin error; `tutors` acepta/filtra `universidades`.

---

## Feature F5 — Contacto de emergencia y anexos del interno se mueven a `interno` (refactor 2026-07)

### T-F5.1 — Reubicar contacto de emergencia y adjunto de DJ del estudiante al internado (`apps/internados/`)

Motivo: el contacto de emergencia y las declaraciones juradas del interno **aplican al internado concreto**, no al estudiante (que puede tener varios internados en el tiempo). Supersede **T-F2.2**.

- **Modelo:** mover `contacto_emergencia_nombre` (char 255, blank), `contacto_emergencia_telefono` (char 30, blank) y `contacto_emergencia_parentesco` (FK `RelationshipType`, PROTECT, null/blank) de `Student` a `Internship`.
- **Serializers:** agregar los 3 campos (opcionales) a `InternshipWriteSerializer` e `InternshipUpdateSerializer`, y exponerlos en `InternshipReadSerializer`. Quitarlos de `Student` (queda `fields="__all__"`, auto). Quitar las columnas de la **carga masiva** (`_crear_estudiante_desde_fila`) — la carga solo crea estudiantes.
- **Services:** `crear_internado` e `actualizar_internado` persisten el contacto de emergencia. `_declaraciones_completas` cruza los `Document` `ACTIVO` del **internado** (ct `internship`), no del estudiante. `notificar_registro_interno` apunta las URLs a `interns/{id}/annex-…`.
- **ViewSets:** quitar `AnnexAttachmentMixin`/`annex_actor` de `StudentViewSet` (y su override `annex_upload`); agregarlos a `InternshipViewSet` (`annex_actor="INTERNO"`), con override `annex_upload` que tras adjuntar llama `services.recalcular_estado_declaraciones(internado)`. `InternshipViewSet.permission_classes` añade `IsUniversityOrReadOnly` (habilita al rol `Interno` las acciones de anexo).
- **Alcance del `Interno`:** `selectors.internados_visibles` e `InternshipScope` reconocen el perfil del `Interno` sobre su `Student` (ct `student`) para ver/adjuntar **su propio internado**.
- **Migración a mano:** `0015_move_emergency_contact_to_internship` — `AddField` (interno) × 3 con `preserve_default=False` en los char; `RunPython` que copia el contacto del estudiante al internado y **re-apunta** los `documento` de anexos `INTERNO` de `estudiante` a su internado (best-effort, al internado más reciente); `RemoveField` (estudiante) × 3. Deps: `internados 0014`, `convenios 0011`.
- **Documentación:** `docs/db_schema_modulo_02_internados.md` (columnas en `interno`, nota en `estudiante`, mapeo de anexos `INTERNO → interno`, carga masiva sin contacto de emergencia), ER global, `db_schema.html`, `api_almacenamiento_frontend.md`, `api_accesos_frontend.md`, `CLAUDE.md`, diccionario regenerado.
- **Criterio:** `Student` sin columnas de contacto; `Internship` con ellas; rutas `intern-annex-upload`/`intern-annex-checklist` presentes y `student-annex-*` ausentes; `makemigrations --check` sin pendientes; `check` limpio; `spectacular` sin error.

---

## Feature F6 — Eliminar `anio_academico` de `estudiante` (refactor 2026-07)

Motivo: el campo `anio_academico` de la tabla `estudiante` (modelo `Student`) es **redundante** con `periodo_academico` (FK → `AcademicPeriod`, que ya identifica el año/periodo lectivo, p. ej. `2025-01`). Decisión del usuario: eliminarlo del modelo, la carga masiva y la documentación. No se sustituye por otro campo.

### T-F6.1 — Quitar el campo del modelo (`apps/internados/models.py`)
- Eliminar la línea `anio_academico = models.PositiveSmallIntegerField("año académico", null=True, blank=True, help_text="Año académico")` del modelo `Student` (~línea inmediatamente antes de `nota_promedio_ponderado`).
- No tocar ningún otro campo. `periodo_academico` (FK, PROTECT) queda como única fuente del periodo/año lectivo.
- **Criterio:** `Student` ya no declara `anio_academico`; `python manage.py check` limpio.

### T-F6.2 — Migración a mano (`apps/internados/migrations/`)
- Crear `0016_remove_student_anio_academico.py` (siguiente número libre; el máximo existente es `0015`) **a mano** (no autogenerar por regla del proyecto).
- Contenido: una sola operación `migrations.RemoveField(model_name="student", name="anio_academico")`.
- `dependencies`: `[("internados", "0015_move_emergency_contact_to_internship")]`.
- **Riesgo documentado:** el `RemoveField` **elimina la columna y cualquier dato existente** en `estudiante.anio_academico` — pérdida **intencional e irreversible** (el dato es reconstruible desde `periodo_academico`). No se agrega `RunPython` de respaldo por decisión de diseño.
- **Criterio:** tras crear la migración, `python manage.py makemigrations --check --dry-run` no reporta cambios pendientes; `migrate` aplica el drop de columna sin error.

### T-F6.3 — Carga masiva: ignorar la columna `anio_academico` del Excel (`apps/internados/services.py`)
- En `_crear_estudiante_desde_fila`: eliminar el bloque de parseo de `anio` (`anio = obtener("anio_academico")` con su validación/conversión, ~líneas 749–757) y quitar el kwarg `anio_academico=anio` del `Student.objects.create(...)` (~línea 776).
- **Decisión de diseño (documentar en el schema):** la trama `TramaCargaEstudiante.xlsx` **puede seguir trayendo** la columna `anio_academico`; debe **ignorarse silenciosamente** (no se lee, no se valida, no rompe el lote si viene). **No** es columna requerida ni opcional-mapeada: simplemente no se procesa. No agregarla a ninguna lista de columnas requeridas/esperadas ni a `CARGA_ALIAS_COLUMNAS`.
- **Criterio:** una fila del Excel con o sin `anio_academico` produce el mismo `Student`; no queda ninguna referencia a `anio_academico` en `services.py`.

### T-F6.4 — Serializers: verificación (`apps/internados/serializers.py`)
- `StudentSerializer` usa `Meta.fields = "__all__"`: al quitar el campo del modelo, **desaparece automáticamente** del serializer (read y write). **No requiere cambio de código**, solo **confirmar** que ni `StudentSerializer` ni ningún otro serializer del módulo referencian `anio_academico` de forma explícita (verificado: no lo hacen).
- **Criterio:** el esquema OpenAPI del `Student` ya no expone `anio_academico`; `python manage.py spectacular --validate` sin error.

### T-F6.5 — ViewSets / endpoints: verificación (`apps/internados/views.py`)
- Confirmar que `StudentViewSet` (CRUD `students`) y la acción `students/bulk-upload/` **no referencian** `anio_academico` explícitamente (verificado: no lo hacen — el CRUD delega en el serializer `__all__` y el bulk-upload en `_crear_estudiante_desde_fila`, ya cubierto por T-F6.3).
- **Criterio:** ninguna vista/acción del módulo menciona `anio_academico`.

### T-F6.6 — Sincronizar documentación del schema (`docs/`)
- `docs/db_schema_modulo_02_internados.md`:
  - Quitar la fila `| \`anio_academico\` | int | Sí | Año académico |` de la **estructura de la tabla `estudiante`** (~línea 136).
  - En la **tabla de columnas de la carga masiva** (estructura del Excel, ~línea 310): quitar la fila `anio_academico` y añadir una nota de que, si la trama la incluye, la columna se **ignora** (coherente con T-F6.3).
  - Revisar y ajustar cualquier otra mención de `anio_academico` en el documento.
- `docs/db_schema.html`: quitar la entrada `["anio_academico","int",true,"","",""]` de la definición de columnas de `estudiante` (~línea 301).
- `docs/db_schema_er_global.md`: si lista `anio_academico` en `estudiante`, quitarlo (verificar).
- `docs/diccionario_datos.docx`: **regenerar** con `docs/generar_diccionario.py` (tras aplicar los cambios de modelo y schema) para que no liste el campo. No editar el `.docx` a mano.
- **Criterio:** ninguna búsqueda de `anio_academico` en `docs/` devuelve resultados en tablas de `estudiante` (salvo la nota de "columna del Excel ignorada").

### T-F6.7 — Sincronizar frontend (`../renads-frontend/`, mismo git root)
- `lib/api/schema.d.ts`: tipo generado del OpenAPI — se **regenera** desde el schema del backend (no editar a mano si el pipeline lo regenera); anotado aquí para que quede sin `anio_academico?` en `Student` (aparece en 2 ocurrencias, ~líneas 5393 y 5939).
- `lib/internados/persons.ts`: quitar el campo del formulario/columnas/tipos — eliminar la entrada `{ name: "anio_academico", label: "Año académico", type: "number" }` (~línea 90) de la definición de campos del estudiante.
- **Criterio:** el formulario de estudiante del frontend ya no muestra "Año académico"; el tipo generado del `Student` no incluye `anio_academico`.

### Criterios de aceptación transversales de F6
- No queda ninguna referencia a `anio_academico` en `apps/internados/` (modelo, services, serializers, views) ni en la documentación de la tabla `estudiante`.
- La carga masiva funciona con tramas que aún incluyan la columna `anio_academico` (se ignora) y con tramas que no la incluyan.
- `manage.py check` limpio; `makemigrations --check` sin pendientes; `spectacular --validate` sin error.
- Convenciones RENADS respetadas (código/identificadores inglés; `.md`/notas español).

---

## Referencias

- **Reglas de negocio (§6 módulo 2):** RN-2/3/4 → T3.1; RN-5 (tutor) → T3.1; RN-6 (1 año) → T3.1; RN-8 (mismo ámbito) → T3.4; RN-9 (máx 4) → T3.4; RN-10 (autoridad suscrita) → T3.5; RN-11 (sin autorización no inicia) → T3.6; RN-12 (fechas) → T3.4; RN-13 (campos clínicos) → T3.1; RN-14 (cambio tutor) → T3.3; RN-15 (bitácora) → historiales + `registrar_auditoria`; **RN-16 (registro masivo Excel)** → T3.8 + acción `students/bulk-upload`; **RN-17 (asignación a campos clínicos disponibles)** → T3.1; **RN-18 (prelación por `nota_promedio_ponderado`)** → T3.9; **RN-19 (periodo académico vs. especialidad según nivel académico)** → T3.10 (helper de services), invocada por T1.6 (`StudentSerializer.validate`) y T3.8 (bulk-upload). Deriva `nivel = estudiante.carrera_profesional.nivel_academico.codigo`: `PREGRADO` ⇒ `periodo_academico` requerido / `especialidad` nula; otro nivel ⇒ `especialidad` requerida / `periodo_academico` nula.
- **Requerimientos:** RF-IN-01..24. **(F2)** RNF-DOC-01/02/03 (gestión documental PDF de anexos), RNF-DOC-04 (versionado), RNF-AUD-01/02 (auditoría del adjunto).
- **Schema:** `docs/db_schema_modulo_02_internados.md`. No inventar campos. **(F1)** tablas nuevas `periodo_academico` (`AcademicPeriod`: `codigo`/`nombre`/`activo`) y `documentos_anexos` (`AnnexDocument`: `codigo`/`nombre`/`activo`/`descripcion`/`obligatorio`); columnas nuevas en `estudiante`: `periodo_academico_id` (FK→`periodo_academico`, PROTECT, nullable) y `especialidad_id` (FK→`especialidad`, SET_NULL, nullable). Módulo 1: registro `nivel_academico.codigo` `CARRERA_PROFESIONAL` → `PREGRADO`. **(F2)** columna nueva en `documento`: `documento_anexo_id` (FK→`documentos_anexos`, SET_NULL, nullable) — definida en el módulo 1 (`apps/convenios/models.py Document`), ver `spec/almacenamiento.md` Etapa 2. **(F6)** columna eliminada de `estudiante`: `anio_academico` (int, nullable) — redundante con `periodo_academico`.
- **Reutilización módulo 1:** `Convention`, `ClinicalField`, `Ipress`, `University`, `ConventionParticipant`, `Specialty`, `ProfessionalCareer`/`AcademicLevel`; `apps/common` (permisos, auditoría) y el patrón `AuditedModelViewSet`/`IsAdminRoleOrReadOnly`; factories `_catalog_viewset`/`_entity_viewset` de `apps/convenios/views.py`. **(F2)** mixin `AnnexAttachmentMixin` y serializer `AnnexUploadSerializer` de `apps/convenios/mixins.py`/`serializers.py`; service `adjuntar_documento` (`apps/common/services.py`); backend `get_document_storage()` (`apps/common/storage.py`).

## Fuera de alcance (este spec)
Testing automatizado; reportes/exportación. **(F2)** el adjunto real de las declaraciones juradas **por estudiante** (actor `INTERNO`) **ya está en alcance** vía **T-F2.2** (acciones `annex-upload`/`annex-checklist`); el adjunto de los demás actores (`AUTORIDAD_UNIVERSIDAD`, `REPRESENTANTE`) se especifica en `spec/almacenamiento.md` Etapa 2. **(F3)** el **estado de las declaraciones juradas** del interno (`estado_declaraciones`: PENDIENTE/COMPLETAS/OBSERVADAS/VALIDADAS con revisión humana) **ya está en alcance** vía **T-F3.5**; el registro por universidad con alcance, la unicidad por DNI, el onboarding del interno (usuario + correo) están en **T-F3.1..T-F3.4**. Siguen fuera de alcance: una tabla puente dedicada estudiante↔anexo (se usa el `Document` polimórfico con FK `documento_anexo`); expiración/rotación de la clave temporal y el bloqueo server-side de endpoints hasta el cambio de clave (el backend solo expone el flag `debe_cambiar_password`); expiración automática de sesión (RNF-SEG-07).
