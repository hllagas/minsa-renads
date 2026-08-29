# Validación — Campos clínicos: Registro (CONAPRES) y Asignación (Órgano Regional)

Fecha: 2026-08-13 · Spec: `spec/convenios_campos_clinicos.md` · Alcance: T-M*, T-S*, T-SEL*, T-SER*, T-P*, T-F*, T-V*, T-I*, T-MIG* (se EXCLUYEN por indicación T-D* y cierre T-C*).

## Resultado: APROBADO — sin errores altos/medios

Se genera la guía de pruebas: `spec/convenios_campos_clinicos.guia_pruebas.md`.

---

## Comprobaciones ejecutadas

- `manage.py check` → **sin errores**.
- `manage.py makemigrations --check --dry-run` → **No changes detected** (modelos y migraciones sincronizados).
- Router: `clinical-field-registrations` y `clinical-field-allocations` exponen list + detalle (CRUD completo vía `ModelViewSet`). La action anidada `conventions/{id}/campos-clinicos/` ya no existe.
- Tablas en BD: `campo_clinico` renombrada a `campo_clinico_ipress`; existe `campo_clinico_ipress_universidad`.
- Data migration (verificada sobre datos reales del `db.sqlite3`): cada registro preexistente tiene 1 asignación con `autorizados == registrados` y `universidad == convenio.universidad`; `campos_clinicos_asignados` == suma real en los 6 registros. El internado preexistente quedó repuntado a una `ClinicalFieldAllocation` válida.
- Reaplicación forward de `internados.0017` sobre datos reales (tras desaplicarla): repunta correctamente el internado a la asignación. Migración forward robusta.
- Reglas de negocio probadas en shell (con rollback, sin mutar la BD):
  - Disponibilidad: `registrados=10`, asignación de 6 pasa; una de 5 falla con clave `campos_clinicos_autorizados`.
  - Acumulador recalculado tras create (6) y tras delete (→0).
  - Universidad ≠ convenio.universidad → `ValidationError` clave `universidad`.
  - Convenio no vigente → `ValidationError` clave `convenio`.
  - Registro: no bajar `campos_clinicos_registrados` por debajo de `campos_clinicos_asignados` → clave `campos_clinicos_registrados`.
  - `select_for_update` presente en los tres services de asignación (T-S4/S5/S6).
- Auditoría: crear un registro produce exactamente **1** entrada `CREAR` (sin doble auditoría). `perform_create`/`perform_update`/`perform_destroy` de ambos viewsets delegan solo en el service (no llaman a `super()` ni a `serializer.save()` + `registrar_auditoria`).
- Sin referencias colgadas en código a `ClinicalField`/`definir_campo_clinico`/`campos_clinicos_de`/`cantidad_maxima`/`ClinicalFieldFilter`/`ClinicalFieldSerializer` fuera de migraciones (grep limpio en `apps/`).
- Internados: `Internship.campo_clinico` → `ClinicalFieldAllocation` (`db_column="campo_clinico_id"`, `PROTECT`, `related_name="internos"`); RN-13 sobre `campos_clinicos_autorizados`; ámbito derivado de `campo_clinico.ipress.ambito_geografico_sanitario_id`; serializers/selectors coherentes (nombre de campo `campo_clinico` sin cambio).

## Cobertura por tarea

| Tarea | Estado |
|-------|--------|
| T-M1 `ClinicalFieldRegistration` (tabla, campos, unique, auditoría, campos eliminados) | OK |
| T-M2 `ClinicalFieldAllocation` (tabla, related_names, unique) | OK |
| T-S1 `crear_registro_campo_clinico` (sede docente, tope convenio, asignados=0, auditoría) | OK |
| T-S2 `actualizar_registro_campo_clinico` (no bajar bajo asignados, asignados no editable) | OK |
| T-S3 `_recalcular_asignados` (fuente única, `Sum … or 0`, `update_fields`) | OK |
| T-S4 `crear_asignacion_campo_clinico` (select_for_update, disponibilidad, coherencia, vigente) | OK |
| T-S5 `actualizar_asignacion_campo_clinico` (disponibilidad excluyendo la propia) | OK |
| T-S6 `eliminar_asignacion_campo_clinico` (recalcula, PROTECT→409) | OK |
| T-S7 retirar `definir_campo_clinico` | OK |
| T-SEL1 retirar `campos_clinicos_de` | OK |
| T-SEL2 `registros_campo_clinico` / `asignaciones_campo_clinico` (select_related) | OK |
| T-SER1 retirar serializer viejo | OK |
| T-SER2 `ClinicalFieldRegistrationSerializer` (disponibilidad, read-only) | OK |
| T-SER3 `ClinicalFieldAllocationSerializer` (fecha_fin ≥ fecha_inicio) | OK |
| T-P1 `IsConapresOrReadOnly` | OK |
| T-P2 `IsRegionalOrganOrReadOnly` (+ `ROL_GOBIERNO_REGIONAL`) | OK |
| T-F1 `ClinicalFieldRegistrationFilter` / `ClinicalFieldAllocationFilter` | OK |
| T-V1 retirar action `campos_clinicos` | OK |
| T-V2 `ClinicalFieldRegistrationViewSet` | OK |
| T-V3 `ClinicalFieldAllocationViewSet` | OK |
| T-V4 registro en router | OK |
| T-I1 FK `Internship.campo_clinico` → `ClinicalFieldAllocation` | OK |
| T-I2 RN-13 sobre `campos_clinicos_autorizados` | OK |
| T-I3 ámbito derivado de la IPRESS | OK |
| T-I4 serializers/selectors internados coherentes | OK |
| T-MIG1 `convenios/0015` (rename+refactor+create+RunPython+removefield) | OK (forward) — ver hallazgo bajo |
| T-MIG2 `internados/0017` (repunte + AlterField) | OK |

---

## Hallazgos no bloqueantes (baja prioridad)

1. **[Bajo] Reverso de `convenios/0015` no soportado y no documentado.**
   Ubicación: `apps/convenios/migrations/0015_clinical_field_registration_allocation.py` (pasos `RemoveField` de `vigencia_inicio`/`vigencia_fin`/`ambito_geografico_sanitario`/`observaciones`).
   Problema: al revertir, el `AddField` inverso de `ambito_geografico_sanitario` (NOT NULL, sin `default`) falla con `IntegrityError: NOT NULL constraint failed`. El criterio T-MIG1 admite "reversible **o** documentado como no soportado con motivo"; la migración no cumple ninguna de las dos vías.
   Corrección sugerida (no bloqueante): añadir una nota en el docstring de la migración indicando que el reverso no está soportado (motivo: columnas NOT NULL eliminadas sin valor por defecto y datos ya migrados a la nueva estructura). Alternativamente, mover los cuatro `RemoveField` a `state_operations`/`separate_database_and_state` o `RunPython.noop` documentado. La ruta **forward** (producción) está verificada y correcta.

2. **[Informativo] Tareas de documentación T-D1..T-D5 pendientes** (excluidas de esta validación por indicación): `docs/db_schema_modulo_01_convenios.md` §9 aún describe la tabla `campo_clinico` antigua con `cantidad_maxima`/`vigencia_*`/`ambito_geografico_sanitario`/`observaciones`; `docs/db_schema_er_global.md`, `docs/db_schema_modulo_02_internados.md`, docs de accesos y `CLAUDE.md` (RN-25) por actualizar. No bloquean el código.

3. **[Informativo] Cierre T-C1 `/code-review` y T-C2 `/fix-types` pendientes** (excluidos por indicación).

---

## Notas

- `select_for_update()` se ejecuta correctamente; en SQLite (dev) es no-op sin error, y aporta el bloqueo real en PostgreSQL (prod). Correcto.
- El acumulador `campos_clinicos_asignados` solo lo escribe `_recalcular_asignados` (fuente única) — confirmado.
- No se detectaron problemas de arquitectura: vistas delgadas (delegan en services/selectors), naming inglés-clase / español-columna respetado, permisos por rol correctos.
