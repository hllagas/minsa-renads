# Validación — Módulo `convenios`, bloque Núcleo + Services

Revisión del agente **validator** contra `spec/convenios.md`, `docs/arquitectura_desarrollo.md` y `docs/db_schema_modulo_01_convenios.md`.

**Alcance revisado:** T2 (selectors), T3 (services), y el núcleo de T1/T4/T5/T6/T7 (`Convention`, plantillas, acciones de flujo). CRUD de catálogos/entidades, ViewSets standalone de flujo y `Document` son de bloques posteriores (no se evalúan aquí).

## Sanidad técnica
- `manage.py check` → sin issues.
- `makemigrations --check` → sin cambios pendientes.
- OpenAPI (`spectacular`) → 0 errores; 13 paths del núcleo.
- Smoke test de flujo (RN-3, vigencia 4/3 años, bloqueo de firma por observación, historial, auditoría) → correcto.

## Conformidad
- Arquitectura: lógica de negocio en `services.py`; vistas delgadas; lecturas en `selectors.py`; permisos y filtros presentes; router bajo `/api/v1/`. ✓
- Schema: campos usados existen en los modelos (`Convention`, `TechnicalEvaluation`, `ConapresOpinion`, `ClinicalField`, `LegalOpinion`, `Signature`, `Publication`); sin campos inventados. ✓
- RN: RN-3 (Específico→Marco vigente), CONAPRES/campos clínicos solo Específico, no firmar con observaciones pendientes, trazabilidad (historial + bitácora) → implementadas. ✓
- Convenciones de idioma: clases inglés, campos/`help_text` español, endpoints inglés. ✓

## Hallazgos

| # | Sev | Ubicación | Problema | Corrección sugerida |
|---|-----|-----------|----------|---------------------|
| 1 | ✅ resuelto | `apps/convenios/permissions.py` `ConventionScope` | ~~Inconsistencia de alcance: el chequeo de objeto solo consideraba al solicitante; un participante veía el convenio en el listado pero recibía 403 en detalle.~~ **Corregido:** nueva clase `ConventionScope.has_object_permission` permite acceso si la entidad del usuario es solicitante **o** participante. Verificado: detalle como participante → 200. |
| 2 | 🟡 baja | `apps/convenios/views.py` acción `participantes` (POST) | `ConventionParticipant` tiene `unique_together (convenio, tipo_contenido, id_objeto)`; agregar un participante duplicado provoca `IntegrityError` (500) en vez de 400. | Validar duplicado en el service `agregar_participante` y lanzar `ValidationError`, o capturar `IntegrityError`. |
| 3 | 🟡 baja | `apps/convenios/services.py` `actualizar_convenio` | Si se actualiza `fecha_inicio` no se recalcula `fecha_fin` (queda la vigencia anterior). | Recalcular `fecha_fin` cuando cambie `fecha_inicio` y no se envíe `fecha_fin` explícito (misma regla que `crear_convenio`). |
| 4 | 🟡 baja | `apps/convenios/serializers.py` `ConventionWriteSerializer` | En `PUT` exige reenviar `tipo_convenio`/`solicitante_*` aunque `actualizar_convenio` los ignora (no editables). Confunde el contrato. | Documentar que la edición es vía `PATCH`, o separar un serializer de actualización con solo los campos editables. |

## Resultado (bloque Núcleo)

**Bloque aprobado.** El hallazgo #1 (medio) fue **corregido y verificado**. Los hallazgos #2–#4 (bajos) quedan agendados.

---

# Validación — bloque Catálogos + Entidades

Revisión de los ViewSets de catálogos (solo lectura) y entidades (CRUD), factories `_catalog_viewset`/`_entity_viewset`, `RepresentativeViewSet` y registro en router.

## Sanidad técnica
- `manage.py check` → sin issues; `makemigrations --check` → sin cambios.
- OpenAPI → 0 errores; 78 paths.
- Verificado: catálogo read-only (200), CRUD universidad (201), `Representative` inválido→400 / válido→201, alcance participante→200.

## Conformidad
- Catálogos expuestos como **solo lectura** (`ReadOnlyModelViewSet`). ✓
- Entidades con CRUD; `Representative` valida el content type polimórfico. ✓
- Idioma/endpoints/clases conforme. ✓

## Hallazgos

| # | Sev | Ubicación | Problema | Corrección sugerida |
|---|-----|-----------|----------|---------------------|
| 5 | 🔴 alta | `views.ENTITY_VIEWSETS["user-entity-profiles"]` | `UserEntityProfile` es CRUD para **cualquier miembro institucional** → un usuario podría crear su propio perfil vinculándose a cualquier entidad/rol (**escalación de privilegios**). | Restringir a superusuario / rol `Administrador RENADS` (permiso dedicado), o sacarlo del router público. |
| 6 | 🟠 media | factory `_entity_viewset` (todas las entidades) | Cualquier miembro institucional puede **crear/editar/eliminar** universidades, GORE, IPRESS, etc. (incluye DELETE) sin restricción de rol. | Aplicar permiso por rol (`Administrador RENADS`) o `DjangoModelPermissions` para escritura; lectura abierta a autenticados. |
| 7 | 🟠 media | factory `_entity_viewset` | Las escrituras de entidades **no pasan por services** ni registran `bitacora_auditoria` (RNF-AUD-01 "toda operación crítica"). | Para entidades sensibles, enrutar create/update/delete por services con auditoría, o agregar registro de auditoría en `perform_create/update/destroy`. |
| 8 | 🟡 baja | `RepresentativeSerializer.validate_tipo_contenido` | Valida el tipo de entidad pero no que `id_objeto` exista en esa tabla. | Validar existencia del objeto referenciado (consulta al modelo del content type). |

## Resultado (bloque Catálogos + Entidades)

**Bloque aprobado.** Hallazgos #5–#8 **corregidos y verificados**:
- #5: `user-entity-profiles` ahora `IsAdminRole` (miembro 403 / admin 200).
- #6: entidades con `IsAdminRoleOrReadOnly` (escritura admin 201 / miembro 403; lectura 200).
- #7: `AuditedModelViewSet` registra create/update/delete en `bitacora_auditoria`.
- #8: `RepresentativeSerializer.validate` verifica existencia de `id_objeto` (inexistente 400).

---

## Estado final del módulo `convenios`

| Hallazgo | Severidad | Estado |
|----------|-----------|--------|
| #1 alcance participante | media | ✅ resuelto |
| #2 participante duplicado (IntegrityError) | baja | ⏳ pendiente |
| #3 `fecha_fin` no recalcula en update | baja | ⏳ pendiente |
| #4 PUT exige campos no editables | baja | ⏳ pendiente |
| cross-tenant en `create` (descubierto en internados #1) | media | ✅ resuelto — `exigir_ambito` en `ConventionViewSet.create` |
| #5 escalación de privilegios en perfiles | **alta** | ✅ resuelto |
| #6 CRUD entidades sin rol | media | ✅ resuelto |
| #7 escrituras sin auditoría | media | ✅ resuelto |
| #8 representante sin validar id | baja | ✅ resuelto |

Resueltos los de severidad alta y media. Quedan **#2, #3, #4 (bajos)** agendados. El módulo `convenios` está funcionalmente completo y seguro para el MVP.
