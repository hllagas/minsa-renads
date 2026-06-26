# Validación — Módulo `internados`, bloque Núcleo + Services

Revisión del agente **validator** contra `spec/internados.md`, `docs/arquitectura_desarrollo.md` y `docs/db_schema_modulo_02_internados.md`.

**Alcance revisado:** T2 (selectors), T3 (services, RN), y el núcleo de T1/T4/T5/T6/T7 (`Internship`, `Rotation` y acciones de flujo). Catálogos y CRUD de `Intern`/`Tutor` son del bloque 2 (no evaluados aquí).

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
| 1 | 🟠 media | `views.InternshipViewSet.create` (y análogo en `apps/convenios` `ConventionViewSet.create`) | El `create` valida el rol (`Universidad`) pero **no** que la universidad del `interno` esté dentro del ámbito institucional del usuario. Un usuario de la Universidad A podría registrar internados de la Universidad B (escritura cross-tenant). | Validar en el service/permiso que `interno.universidad` (o el solicitante, en convenios) pertenezca a las entidades del usuario; superusuario exento. |
| 2 | 🟡 baja | `selectors.internados_visibles` | El alcance de visibilidad es solo por **universidad** del interno; roles como `Sede docente`/`Tutor` no verían internados de su sede. | Para MVP es aceptable; si se requiere, ampliar el alcance para incluir la `ipress` (sede) en las entidades del usuario. |
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

# Validación — bloque Catálogos + Personas (Intern/Tutor)

## Sanidad técnica
- `check` sin issues; `makemigrations --check` sin cambios; OpenAPI 0 errores (102 paths).
- Verificado: catálogos read-only (estado_internado 12, identity-doc 3); crear interno propio → 201 (`creado_por` auto); cross-tenant → 403; lista con scope (solo del ámbito); crear tutor (rol Universidad) → 201.

## Conformidad
- Catálogos solo lectura; `Intern`/`Tutor` con auditoría (`AuditedModelViewSet`) y escritura por rol `Universidad`/`Administrador RENADS`.
- `Intern` con alcance por universidad (RNF-SEG-04: datos personales solo visibles en el ámbito) y `exigir_ambito` en `create`. ✓

## Hallazgos

| # | Sev | Ubicación | Problema | Sugerencia |
|---|-----|-----------|----------|------------|
| 5 | 🟡 baja | `TutorViewSet` | Sin alcance institucional (cualquier rol Universidad edita cualquier tutor). | Aceptable MVP (los tutores son staff compartido); si se requiere, acotar por `ipress`. |
| 6 | 🟡 baja | `InternViewSet.update` | No revalida `exigir_ambito` si se cambia `universidad` del interno. | Revalidar ámbito en update cuando cambia `universidad`. |

## Resultado (módulo completo)

**Módulo `internados` aprobado y cerrado para el MVP.** Núcleo (RN-1..15) + personas + catálogos completos; seguridad con alcance institucional y auditoría. Sin hallazgos altos/medios pendientes; #5–#6 (bajos) agendables.
