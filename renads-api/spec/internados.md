# Spec — Módulo `internados` (Registrar Internados)

Tareas exactas para `apps/internados/` según [arquitectura](../docs/arquitectura_desarrollo.md) y [schema M2](../docs/db_schema_modulo_02_internados.md). Producido por el agente **spec** (SDD). Patrón ya establecido en el módulo `convenios` (services/selectors, ViewSets delgados, JWT + alcance institucional, auditoría transversal, escritura de master-data solo `Administrador RENADS`).

## Resumen

Exponer vía DRF (bajo `/api/v1/`) los recursos del módulo: catálogos (solo lectura), `Intern` y `Tutor` (CRUD), y el núcleo `Internship`/`Rotation` con su flujo y reglas de negocio. Reutiliza modelos del módulo 1 (`Convention`, `ClinicalField`, `Ipress`, `University`, `ConventionParticipant`).

**Convenciones:** clases inglés; campos/tablas/`help_text` español; endpoints inglés; docstrings español. Sin tests (fuera de alcance MVP). Reutilizar `apps/common` (permisos, auditoría) y el patrón `AuditedModelViewSet`.

**Entidades** (modelos en `apps/internados/models.py`):
- Catálogos: `InternshipStatus`, `RotationStatus`, `ServiceArea`, `IdentityDocumentType`.
- Personas: `Intern`, `Tutor`.
- Núcleo: `Internship`, `InternshipStatusHistory`, `TutorHistory`, `Rotation`, `RotationAuthorization`, `RotationStatusHistory`.

---

## Bloques sugeridos
- **Bloque 1 (núcleo + services):** selectors, services (todas las RN), serializers de `Internship`/`Rotation` + entradas de acciones, `InternshipViewSet`/`RotationViewSet` con acciones de flujo, permisos, filtros, router del núcleo.
- **Bloque 2 (catálogos + personas):** catálogos read-only, CRUD de `Intern` y `Tutor`, filtros, registro en router.

---

## T1 — Serializers (`apps/internados/serializers.py`)

- **T1.1** `InternshipReadSerializer` (anida interno, convenio, ipress, tutor, estado legibles) / `InternshipWriteSerializer` (FKs; `estado_actual`, `creado_por`, `fecha_fin` calculados/solo lectura si aplica).
- **T1.2** `RotationReadSerializer` / `RotationWriteSerializer` (`internado` se toma de la URL en acciones anidadas; `estado_actual`, `numero_rotacion`, `creado_por` solo lectura — los fija el service).
- **T1.3** Entradas de acciones: `CambiarEstadoInternadoSerializer` (estado_codigo, observacion), `CambiarTutorSerializer` (tutor, fecha_cambio, motivo), `RotationAuthorizationSerializer` (participante_convenio, resultado, fecha_autorizacion, observaciones).
- **T1.4** Historiales: serializers de `InternshipStatusHistory`, `TutorHistory`, `RotationStatusHistory`.
- **T1.5** `Intern` y `Tutor`: `ModelSerializer` (CRUD). Catálogos: serializers de solo lectura.

**Criterio:** `Internship` y `Rotation` tienen read/write; campos controlados por services marcados `read_only`.

---

## T2 — Selectors (`apps/internados/selectors.py`)

- **T2.1** `internados_visibles(usuario)`: queryset de `Internship` filtrado por alcance institucional (la universidad del interno dentro de las entidades del usuario; superusuario ve todo; sin perfiles → ninguno). Reutilizar `apps/common/selectors`.
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
  - **RN-13:** el `campo_clinico` pertenece al convenio y no excede su `cantidad_maxima` (contar internados/uso del campo clínico).
  - Coherencia de ámbito: `ambito_geografico_sanitario` consistente con el `campo_clinico`/`ipress`.
  - Estado inicial `REGISTRADO`; `creado_por = usuario`.
- **T3.2** `cambiar_estado_internado(internado, nuevo_estado_codigo, usuario, observacion="")`.
- **T3.3** `cambiar_tutor(internado, datos, usuario)` (**RN-14**): registra `TutorHistory` (tutor, fecha_cambio, motivo, responsable=usuario) y actualiza `internado.tutor`.
- **T3.4** `crear_rotacion(internado, datos, usuario)`:
  - **RN-8:** `ipress_origen` e `ipress_destino` deben pertenecer al mismo `ambito_geografico_sanitario` del internado.
  - **RN-9:** el interno no supera **4** rotaciones (asignar `numero_rotacion` = actuales + 1; rechazar si > 4).
  - **RN-12:** `fecha_inicio`/`fecha_fin` dentro del periodo del internado.
  - Estado inicial `SOLICITADA`.
- **T3.5** `autorizar_rotacion(rotacion, datos, usuario)` (**RN-10**): el `participante_convenio` debe ser **firmante** (`es_firmante=True`) del Convenio Específico del internado; crea `RotationAuthorization`; estado `AUTORIZADA`/`OBSERVADA`/`RECHAZADA` según `resultado`.
- **T3.6** `iniciar_rotacion(rotacion, usuario)` (**RN-11**): bloquea si no existe autorización `APROBADO`; pasa a `EN_CURSO`.
- **T3.7** `cambiar_estado_rotacion(rotacion, nuevo_estado_codigo, usuario, observacion="")`.

**Criterio:** cada RN del §6 del módulo está cubierta por un service; ningún cambio de estado fuera de services; auditoría e historial siempre registrados.

---

## T4 — ViewSets (`apps/internados/views.py`)

- **T4.1** Catálogos: `ReadOnlyModelViewSet` (reutilizar factory equivalente).
- **T4.2** `InternViewSet`, `TutorViewSet`: CRUD con auditoría (`AuditedModelViewSet`). Escritura por rol `Universidad`/`Administrador RENADS` (o `IsAdminRoleOrReadOnly` según política).
- **T4.3** `InternshipViewSet` (`ModelViewSet`): `get_queryset = selectors.internados_visibles`; create/update vía services; acciones: `cambiar-estado`, `cambiar-tutor`, `historial`, `rotaciones` (GET lista / POST crea rotación).
- **T4.4** `RotationViewSet` (`ModelViewSet`): acciones `autorizar`, `iniciar`, `cambiar-estado`, `historial`. Escritura vía services.

**Criterio:** ViewSets delgados; escritura vía services; lectura vía selectors; serializer read/write por acción.

---

## T5 — Permissions (`apps/internados/permissions.py`)

- **T5.1** Global `IsAuthenticated` + `IsInstitutionalMember`.
- **T5.2** Alcance de objeto sobre `Internship`/`Rotation` por la universidad del interno (clase tipo `InternshipScope`, análoga a `ConventionScope`).
- **T5.3** Acciones por rol: `cambiar-tutor`/registrar interno → `Universidad`; `autorizar` rotación → `Autoridad de convenio`; transiciones administrativas → `Administrador RENADS`. Reutilizar helper `exigir_roles`.

**Criterio:** autorización de rotación restringida a autoridad suscrita (rol + RN-10); alcance institucional aplicado.

---

## T6 — Filters (`apps/internados/filters.py`)

- **T6.1** `InternshipFilter`: por `convenio`, `ipress`, `tutor`, `estado_actual`, `ambito_geografico_sanitario`, rango de `fecha_inicio`/`fecha_fin`; búsqueda por interno (documento/nombre).
- **T6.2** `RotationFilter`: por `internado`, `estado_actual`, `ipress_origen`/`ipress_destino`, `servicio_area`.
- **T6.3** `InternFilter`: por `universidad`, `carrera_profesional`, `especialidad`, `numero_documento`.

**Criterio:** consultas RF-IN-23 (por convenio, universidad, sede, tutor, región, periodo) soportadas.

---

## T7 — URLs / router (`apps/internados/urls.py` + registro en `config/api_urls.py`)

- **T7.1** `DefaultRouter` con basenames en inglés: `interns`, `tutors`, `internships`, `rotations`, y catálogos (`internship-statuses`, `rotation-statuses`, `service-areas`, `identity-document-types`).
- **T7.2** Incluir el router de `internados` en `config/api_urls.py` (bajo `/api/v1/`).
- **T7.3** Verificar OpenAPI incluye los nuevos paths.

**Criterio:** `manage.py check` limpio; `spectacular` sin error; endpoints en el esquema.

---

## Referencias

- **Reglas de negocio (§6 módulo 2):** RN-2/3/4 → T3.1; RN-5 (tutor) → T3.1; RN-6 (1 año) → T3.1; RN-8 (mismo ámbito) → T3.4; RN-9 (máx 4) → T3.4; RN-10 (autoridad suscrita) → T3.5; RN-11 (sin autorización no inicia) → T3.6; RN-12 (fechas) → T3.4; RN-13 (campos clínicos) → T3.1; RN-14 (cambio tutor) → T3.3; RN-15 (bitácora) → historiales + `registrar_auditoria`.
- **Requerimientos:** RF-IN-01..24.
- **Schema:** `docs/db_schema_modulo_02_internados.md`. No inventar campos.
- **Reutilización módulo 1:** `Convention`, `ClinicalField`, `Ipress`, `University`, `ConventionParticipant`; `apps/common` (permisos, auditoría) y el patrón `AuditedModelViewSet`/`IsAdminRoleOrReadOnly` de `apps/convenios`.

## Fuera de alcance (este spec)
Testing automatizado; `Document`/adjuntos (storage externo); reportes/exportación.
