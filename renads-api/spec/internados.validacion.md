# Validación — Módulo `internados`, bloque Núcleo + Services

Revisión del agente **validator** contra `spec/internados.md`, `docs/arquitectura_desarrollo.md` y `docs/db_schema_modulo_02_internados.md`.

**Alcance revisado:** T2 (selectors), T3 (services, RN), y el núcleo de T1/T4/T5/T6/T7 (`Internship`, `Rotation` y acciones de flujo). Catálogos y CRUD de `Student`/`Tutor` son del bloque 2 (no evaluados aquí).

## Sanidad técnica
- `manage.py check` → sin issues.
- `makemigrations --check` → sin cambios (no se tocaron modelos).
- OpenAPI → 0 errores; 12 paths del núcleo.
- Smoke test de flujo (todas con rollback, sin datos residuales):
  - RN-6 (>1 año) → 400 · internado válido → 201 `REGISTRADO`
  - RN-13 (campo clínico lleno) → 400
  - RN-8 (sedes distinto ámbito) → 400 · rotación válida → `numero_rotacion=1` (RN-9)
  - RN-11 (iniciar sin autorización) → 400
  - RN-10 (autorizar con firmante) → `AUTORIZADA` · iniciar autorizada → `EN_CURSO`
  - Auditoría: 14 registros.

## Conformidad
- Arquitectura: RN en `services.py`; vistas delgadas; lecturas en `selectors.py`; permisos y filtros presentes; router bajo `/api/v1/`. ✓
- Schema: campos de `Internship`/`Rotation`/historiales correctos; reutiliza módulo 1 (`Convention`, `ClinicalField`, `Ipress`, `University`, `ConventionParticipant`). ✓
- RN: 2/3/4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15 cubiertas por services + historiales + auditoría. ✓
- Convenciones de idioma. ✓

## Hallazgos

| # | Sev | Ubicación | Problema | Corrección sugerida |
|---|-----|-----------|----------|---------------------|
| 1 | 🟠 media | `views.InternshipViewSet.create` (y análogo en `apps/convenios` `ConventionViewSet.create`) | El `create` valida el rol (`Universidad`) pero **no** que la universidad del `estudiante` esté dentro del ámbito institucional del usuario. Un usuario de la Universidad A podría registrar internados de la Universidad B (escritura cross-tenant). | Validar en el service/permiso que `estudiante.universidad` (o el solicitante, en convenios) pertenezca a las entidades del usuario; superusuario exento. |
| 2 | 🟡 baja | `selectors.internados_visibles` | El alcance de visibilidad es solo por **universidad** del estudiante; roles como `Sede docente`/`Tutor` no verían internados de su sede. | Para MVP es aceptable; si se requiere, ampliar el alcance para incluir la `ipress` (sede) en las entidades del usuario. |
| 3 | 🟡 baja | `services.actualizar_internado` | Al cambiar `ipress` no se revalida que pertenezca al ámbito geográfico del internado. | Revalidar `ipress.ambito_geografico_sanitario` contra `internado.ambito_geografico_sanitario` en la actualización. |
| 4 | 🟡 baja | `serializers.InternshipWriteSerializer` | `PUT` exige reenviar campos no editables por `actualizar_internado`. | Documentar edición vía `PATCH` o serializer de actualización con solo campos editables (mismo criterio que convenios #4). |

## Resultado

**Bloque aprobado.** Hallazgos #1–#4 **corregidos y verificados**:
- #1: `exigir_ambito` en `create` (convenios + internados) — cross-tenant → 403; admin/superusuario exentos; propio → 201.
- #2: `internados_visibles` e `InternshipScope` ahora incluyen la **sede (IPRESS)** además de la universidad.
- #3: `actualizar_internado` revalida que la `ipress` pertenezca al ámbito del internado (fuera de ámbito → 400).
- #4: `InternshipUpdateSerializer` (solo campos editables) para `update`.

Las 11 reglas de negocio funcionan y se auditan. Módulo `internados` (núcleo) listo.

---

# Validación — bloque Catálogos + Personas (Student/Tutor)

## Sanidad técnica
- `check` sin issues; `makemigrations --check` sin cambios; OpenAPI 0 errores (102 paths).
- Verificado: catálogos read-only (estado_internado 12, identity-doc 3); crear estudiante propio → 201 (`creado_por` auto); cross-tenant → 403; lista con scope (solo del ámbito); crear tutor (rol Universidad) → 201.

## Conformidad
- Catálogos solo lectura; `Student`/`Tutor` con auditoría (`AuditedModelViewSet`) y escritura por rol `Universidad`/`Administrador RENADS`.
- `Student` con alcance por universidad (RNF-SEG-04: datos personales solo visibles en el ámbito) y `exigir_ambito` en `create`. ✓

## Hallazgos

| # | Sev | Ubicación | Problema | Sugerencia |
|---|-----|-----------|----------|------------|
| 5 | 🟡 baja | `TutorViewSet` | Sin alcance institucional (cualquier rol Universidad edita cualquier tutor). | Aceptable MVP (los tutores son staff compartido); si se requiere, acotar por `ipress`. |
| 6 | 🟡 baja | `StudentViewSet.update` | No revalida `exigir_ambito` si se cambia `universidad` del estudiante. | Revalidar ámbito en update cuando cambia `universidad`. |

## Resultado (módulo completo)

**Módulo `internados` aprobado y cerrado para el MVP.** Núcleo (RN-1..15) + personas + catálogos completos; seguridad con alcance institucional y auditoría. Sin hallazgos altos/medios pendientes; #5–#6 (bajos) agendables.

---

# Validación — Feature F1 (Periodo académico, anexos y RN-19) — 2026-07-20

**Alcance:** bloque **Feature F1** de `spec/internados.md` (T1.6, T3.8, T3.10, T4.2/T4.5, T6.3, T7.4), schema `docs/db_schema_modulo_02_internados.md` y convenciones `CLAUDE.md`.

## Resultado

**VALIDACIÓN EXITOSA — sin errores altos ni medios.** Todos los criterios de aceptación de F1 se cumplen. Se genera `spec/internados.guia_pruebas.md`.

## Verificaciones ejecutadas (solo lectura/diagnóstico)

| Comando | Resultado |
|---------|-----------|
| `manage.py check` | `System check identified no issues (0 silenced).` |
| `manage.py makemigrations --check --dry-run` | `No changes detected` |
| `manage.py spectacular --file schema.yml` | `Errors: 0`; paths `/api/v1/academic-periods/`, `/api/v1/academic-periods/{id}/`, `/api/v1/annex-documents/`, `/api/v1/annex-documents/{id}/` presentes. (schema.yml borrado tras verificar.) Los 46 warnings de `spectacular` son preexistentes y transversales a todos los ViewSets — no específicos de F1. |
| Prueba RN-19 en shell (transacción con rollback, sin datos residuales) | Los 4 casos + variantes pasan. |

### Prueba RN-19 (helper `services.validar_regla_periodo_especialidad` + `StudentSerializer.validate`)

- [OK] PREGRADO sin `periodo_academico` -> error `periodo_academico`: "El periodo académico es obligatorio para estudiantes de Pregrado."
- [OK] PREGRADO con `especialidad` -> error `especialidad`: "La especialidad no aplica a estudiantes de Pregrado."
- [OK] MAESTRIA (otro nivel) sin `especialidad` -> error `especialidad`: "La especialidad es obligatoria para este nivel académico."
- [OK] MAESTRIA con `periodo_academico` -> error `periodo_academico`: "El periodo académico solo aplica al nivel Pregrado."
- [OK] PREGRADO con `periodo_academico` y sin `especialidad` -> sin error.
- [OK] MAESTRIA con `especialidad` y sin `periodo_academico` -> sin error.
- [OK] `StudentSerializer.validate` (create) PREGRADO sin periodo -> `serializers.ValidationError`.
- [OK] `StudentSerializer.validate` (update parcial, `attrs={}`) fusiona `self.instance` (carrera/periodo/especialidad) -> no exige campos no reenviados -> sin error.

## Cobertura por tarea

| Tarea | Estado | Evidencia |
|-------|--------|-----------|
| **T-F1.1** rename `CARRERA_PROFESIONAL`->`PREGRADO` | OK | `convenios/migrations/0009_rename_nivel_pregrado.py` (RunPython reversible; `update` por `codigo` sin borrar la fila -> no rompe FKs de `ProfessionalCareer`). `0002_seed_catalogos.py` ya usa `("PREGRADO","Pregrado")`. Única aparición de `CARRERA_PROFESIONAL` en el repo es la migración de rename (esperado). BD verificada: nivel resuelto = `PREGRADO`. |
| **T-F1.2** `AcademicPeriod` (`periodo_academico`) | OK | `models.py:61-66`; migración `0008`. Hereda `Catalog`; `db_table`/`verbose_name` en español. |
| **T-F1.3** `AnnexDocument` (`documentos_anexos`) | OK | `models.py:69-81` con `descripcion` (TextField, blank) y `obligatorio` (Bool default True); migración `0008`. |
| **T-F1.4** FKs `Student.periodo_academico` (PROTECT, null/blank) y `Student.especialidad` (SET_NULL, null/blank) | OK | `models.py:116-125`; migración `0008` con `db_column` correctos. |
| **T-F1.5 / T3.10 / T1.6** RN-19 helper único + serializer + bulk | OK | Helper `services.py:294-320`; `StudentSerializer.validate` (`serializers.py:25-52`) delega y fusiona `self.instance`; `registrar_estudiantes_masivo` invoca el **mismo** helper por fila (`services.py:422-425`) y reporta en `errores` sin abortar el lote. Sin lógica duplicada ni divergente. |
| **T4.2 / T6.3** `filterset_fields` Student += `periodo_academico`, `especialidad` | OK | `views.py:185-188` (fuente única en la vista, sin clase duplicada). |
| **T4.5 / T7.4 / T-F1.6** `ENTITY_VIEWSETS` + router | OK | `views.py:247-256` reutiliza `_entity_viewset` de `apps.convenios.views` (escritura `IsAdminRoleOrReadOnly` = solo `Administrador RENADS`/superuser; lectura autenticados). `urls.py:18-19` loop de registro. |
| Semillas | OK | `internados/0009_seed_periodo_anexos.py`: periodos `2025-I/II`, `2026-I/II` y 4 declaraciones juradas (`obligatorio=True`); idempotente (`update_or_create`) y reversible. |
| Docs <-> código | OK | `db_schema_modulo_02` (§2/§3/§6bis/§9 con RN-19), `db_schema_modulo_01` (nivel `PREGRADO`), `db_schema_er_global` (relaciones `periodo_academico`/`especialidad`/`documentos_anexos`). |

## Observaciones (informativas — no requieren corrección)

- **[Baja / naming]** El spec T3.10 nombra el parámetro del helper como `carrera_profesional`; la implementación usa `carrera`. No es defecto funcional: ambos llamadores invocan con `carrera=...` de forma consistente y el criterio de aceptación se cumple. Se documenta por trazabilidad.
- **[Baja / robustez]** `StudentSerializer.validate` retorna temprano si no hay `carrera_profesional` (`serializers.py:42-43`), delegando la obligatoriedad de la carrera a la validación de campo del `ModelSerializer` (FK `null=False`). Evita `AttributeError` al derivar el nivel sin debilitar la validación.
- **[Baja / convenciones]** Clases en inglés (`AcademicPeriod`, `AnnexDocument`), endpoints en inglés (`academic-periods`, `annex-documents`), `db_table`/columnas/`help_text`/docstrings/`.md` en español. Conforme a `CLAUDE.md`.

**F1 aprobada.** Sin hallazgos altos/medios; observaciones bajas agendables (no bloquean).

---

# Validación — Feature F2 (`documentos_anexos` generalizado a documentos por actor) — 2026-07-20

**Alcance:** tarea **T-F2.1** de `spec/internados.md` (`AnnexDocument.tipo_actor`, endpoint `annex-documents`, migraciones `0010`/`0011`/`0012`), schema `docs/db_schema_modulo_02_internados.md` + ER global + `db_schema.html` y convenciones `CLAUDE.md`.

## Resultado

**VALIDACIÓN EXITOSA — sin errores altos ni medios.** Todos los criterios de aceptación de T-F2.1 se cumplen. Se actualiza `spec/internados.guia_pruebas.md` con la sección F2.

## Verificaciones ejecutadas (solo lectura/diagnóstico)

| Comando | Resultado |
|---------|-----------|
| `manage.py check` | `System check identified no issues (0 silenced).` |
| `manage.py makemigrations --check --dry-run` | `No changes detected` (modelo, migraciones y state-only alineados). |
| `manage.py spectacular --file schema.yml` | `Errors: 0`. Parámetro de query `tipo_actor` (enum `INTERNO`/`AUTORIDAD_UNIVERSIDAD`/`REPRESENTANTE`) presente en `/api/v1/annex-documents/`; `TipoActorEnum` en el componente del serializer. Los 46 warnings son preexistentes y transversales (dynamic `get_queryset`), no de F2. |
| Conteo de semilla por `tipo_actor` (shell) | `{INTERNO: 4, AUTORIDAD_UNIVERSIDAD: 2, REPRESENTANTE: 2}` — coincide con el criterio. |
| Reversibilidad: `migrate internados 0009` y re-`migrate` | `0010`/`0011`/`0012` se desaplican y reaplican sin error; conteo estable tras el ciclo; `makemigrations --check` limpio después. |

## Cobertura por criterio (T-F2.1)

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| Campo `tipo_actor` (`CharField(30)`, choices `ANNEX_ACTOR`, default `INTERNO`, help_text ES) | OK | `models.py:69-83`. `ANNEX_ACTOR` con las 3 tuplas; CONAPRES bajo `REPRESENTANTE`. |
| Endpoint `annex-documents` filtra por `tipo_actor` | OK | `views.py:251-255` `filterset_fields=["tipo_actor","obligatorio","activo"]`; serializer auto (`fields="__all__"`) vía `_entity_viewset`. Parámetro en OpenAPI. |
| Migración AddField default `INTERNO` | OK | `0010_annexdocument_tipo_actor.py` — AddField con default y choices en español. |
| Seed `RESOL_AUTUNI`/`DNI_AUTUNI` (AUTORIDAD_UNIVERSIDAD) + `RESOL_REP`/`DNI_REP` (REPRESENTANTE), `obligatorio=True` | OK | `0011_seed_documentos_actor.py` — `update_or_create` idempotente y reversible (`unseed`). |
| help_text state-only de `descripcion`/`obligatorio` | OK | `0012_annexdocument_help_text.py` — `AlterField` sin cambio de esquema; alineado con el modelo. |
| Docs sincronizados | OK | `db_schema_modulo_02_internados.md` (columna `tipo_actor` + semilla por actor §Valores), `db_schema_er_global.md` (nota nodo `documentos_anexos`), `db_schema.html` (SCHEMA + columna), `CLAUDE.md` (regla del módulo Internados). |
| Spec actualizado | OK | `spec/internados.md` T-F2.1 y la línea del endpoint `annex-documents` (`filterset_fields` con `tipo_actor`). |

## Conformidad

- **Arquitectura:** catálogo maestro vía `_entity_viewset` (escritura solo `Administrador RENADS`, lectura autenticados); router bajo `/api/v1/`; vista delgada. ✓
- **Schema:** tabla `documentos_anexos` y endpoint `annex-documents` conservados; sin campos inventados; nombre de columna en español; coherencia con el `.md`. ✓
- **Convenciones RENADS:** clase inglés (`AnnexDocument`), endpoint inglés (`annex-documents`), `db_table`/columna `tipo_actor`/`help_text`/docstrings/`.md` en español; valores del choice en MAYÚSCULAS técnicas (`INTERNO`/`AUTORIDAD_UNIVERSIDAD`/`REPRESENTANTE`) con etiquetas en español. ✓
- **Decisiones del usuario:** discriminador `tipo_actor` en un solo catálogo (no tabla normalizada); CONAPRES mapeado a `REPRESENTANTE`; adjunto real por entidad fuera de alcance. Respetadas. ✓

## Observaciones (informativas — no requieren corrección)

- **[Baja / orden de seed]** La semilla `INTERNO` (4 declaraciones juradas) se crea en `0009`, que corre **antes** de `0010` (AddField `tipo_actor`). Esas filas toman el default `INTERNO` de la columna al agregarse en `0010`; el conteo final es correcto (`INTERNO: 4`). No es defecto: el orden de dependencias es válido y el resultado verificado.
- **[Baja / naming semilla]** `RESOL_AUTUNI`/`RESOL_REP` y `DNI_AUTUNI`/`DNI_REP` comparten `nombre` ("Resolución de designación del cargo" / "Documento de identidad") entre actores, diferenciados por `codigo` y `descripcion`. Intencional (el actor lo aporta `tipo_actor`); sin colisión de `codigo`.

**F2 aprobada.** Sin hallazgos altos/medios. Docs, spec, modelo y migraciones sincronizados.

---

# Validación — Features F2 (adjunto real de anexos por estudiante) y F3 (onboarding del interno)

**Resultado: APROBADO — sin errores altos/medios.**

Fecha: 2026-07-20. Revisión del `validator` (SDD) contra `spec/internados.md`
(T-F2.2, Feature F3: T-F3.1..T-F3.5, migraciones F3, gate RN-23), `spec/almacenamiento.md`
(Etapa 2), `docs/db_schema_modulo_02_internados.md` y `CLAUDE.md`. No se modificó código.

## Sanidad técnica
- `manage.py check` → **0 issues**.
- `makemigrations --check --dry-run` → **No changes detected**.
- `spectacular` → **0 errores**; rutas `interns/{id}/revisar-declaraciones/`,
  `auth/me/cambiar-password/`, `students/{id}/annex-upload/` y `.../annex-checklist/`
  presentes en el esquema.
- **BD fresca** → migra sin error (grafo válido, incl. `common.0001_initial`,
  `internados.0013`).

## Cobertura F2 (T-F2.2)
- **T-F2.2.1** OK — `StudentViewSet(AnnexAttachmentMixin, AuditedModelViewSet)` con
  `annex_actor="INTERNO"`; CRUD y `bulk-upload` intactos.
- **T-F2.2.2/3** OK — `annex-upload` (override que delega en
  `AnnexAttachmentMixin.annex_upload` y, tras 201, recalcula `estado_declaraciones`
  de los internados en estado bloqueante); `annex-checklist` provista por el mixin.
- **T-F2.2.4** OK — permisos `[IsAuthenticated, IsInstitutionalMember, IsUniversityOrReadOnly]`;
  el rol `Interno` puede `annex_upload`/`annex_checklist` de su propio `Student`
  (`ACCIONES_INTERNO`), con alcance por `estudiantes_visibles` (su propio Student vía
  perfil sobre `Student`).
- **T-F2.2.5** OK — `@extend_schema` en ambas acciones.

## Cobertura F3 (T-F3.1..T-F3.5)
- **T-F3.1 (RN-20)** OK — `InternshipViewSet.create` invoca
  `exigir_ambito(usuario, ContentType(University), estudiante.universidad_id)` +
  `exigir_roles("Universidad")`; superusuario/Administrador exentos vía `exigir_ambito`.
  Lectura con alcance por `internados_visibles`/`estudiantes_visibles`.
- **T-F3.2 (RN-21)** OK — `tiene_internado_vigente(estudiante)` con
  `ESTADOS_INTERNADO_BLOQUEANTES` = {REGISTRADO, PENDIENTE_VALIDACION, OBSERVADO,
  VALIDADO, ACTIVO, EN_ROTACION_SOLICITADA/AUTORIZADA/OBSERVADA}; liberadores
  {SUSPENDIDO, RETIRADO, CULMINADO, ANULADO} no bloquean. `crear_internado` rechaza
  con 400 en español.
- **T-F3.3 (RN-22)** OK — `aprovisionar_interno`: `User username=DNI`, clave temporal
  `secrets.token_urlsafe(16)` (no logueada en claro), `is_staff=False`, grupo `Interno`,
  `UserEntityProfile` sobre el `Student` (`get_or_create` idempotente),
  `UserSecurity.debe_cambiar_password=True`. Reingreso reutiliza el usuario sin resetear
  clave. `UserSecurity` (tabla `seguridad_usuario`, OneToOne) + `apps.common` en
  INSTALLED_APPS con `CommonConfig` y `common/0001_initial`.
- **T-F3.4** OK — `notificar_registro_interno` best-effort vía `transaction.on_commit`;
  incluye sede docente (IPRESS), campo clínico/carrera, fechas, tutor (+correo) e
  instrucción/links de checklist y upload; omite y loguea aviso si no hay correo; un
  fallo de envío no revierte el registro. `EMAIL_BACKEND` consola en `dev`, SMTP por
  `.env` en `prod`; variables en `.env.example`.
- **T-F3.5 (RN-23)** OK — `Internship.estado_declaraciones` (choices
  PENDIENTE/COMPLETAS/OBSERVADAS/VALIDADAS, default PENDIENTE);
  `recalcular_estado_declaraciones` (fuente única; no degrada `VALIDADAS`; PENDIENTE↔COMPLETAS
  según checklist obligatorio); `revisar_declaraciones` (rol Universidad/Administrador,
  resultado VALIDADAS/OBSERVADAS, exige estado COMPLETAS/OBSERVADAS); gate en
  `cambiar_estado_internado`: no `ACTIVO` sin `VALIDADAS`. Historial + auditoría en cada
  transición; `@extend_schema` en `revisar-declaraciones`.

## Auth (Decisión mínima)
- OK — claim `debe_cambiar_password` en el JWT (`CustomTokenObtainPairSerializer`) y campo
  en `MeSerializer` (`/api/v1/auth/me/`); `POST /api/v1/auth/me/cambiar-password/`
  (`MeChangePasswordView`) valida clave actual, aplica validadores de Django y limpia el
  flag. No se implementa expiración de clave temporal ni bloqueo server-side (fuera de
  alcance, coherente con el spec).

## Migraciones y docs
- OK — `internados/0013` (AddField `estado_declaraciones` + seed grupos `Universidad`/`Interno`
  idempotente); `common/0001_initial` (`UserSecurity`). Docs M2, ER/html, `CLAUDE.md` y
  `api_almacenamiento_frontend.md` sincronizados.

## Convenciones RENADS
- Clases inglés; endpoints inglés (`revisar-declaraciones`, `annex-upload`, `cambiar-password`);
  `db_table`/columnas/`help_text`/docstrings/`.md` en español. Escritura vía services;
  vistas delgadas; lecturas vía selectors; alcance institucional aplicado.

## Observaciones menores (severidad baja — no bloquean)
- `[BAJA]` `services.py:244` — el flag `debe_cambiar_password` solo se fuerza en la
  creación (`if creado`); en reingreso el usuario conserva su estado, conforme al spec.
- `[BAJA]` La clave temporal se genera con `secrets` y nunca se envía por correo ni se
  loguea; el interno debe usar el flujo de recuperación/cambio para acceder (esperado en MVP).

Conforme a la regla del validator, se actualiza la guía de pruebas manuales
(`spec/internados.guia_pruebas.md`, secciones F2/F3).
