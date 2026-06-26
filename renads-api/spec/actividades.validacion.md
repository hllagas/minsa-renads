# Validación — Módulo `actividades`

Revisión del agente **validator** contra `spec/actividades.md`, `docs/arquitectura_desarrollo.md` y `docs/db_schema_modulo_03_actividades.md`.

## Sanidad técnica
- `manage.py check` → sin issues.
- `makemigrations --check` → sin cambios (no se tocaron modelos).
- OpenAPI → 0 errores; 112 paths totales (+10 del módulo).
- Smoke test (con rollback): RN-1 (internado no activo)→400 · RN-2 (fuera de periodo)→400 · válida→201 `REGISTRADA` · RN-9 (duplicado)→400 · validar→`OBSERVADA` · subsanar→`SUBSANADA` · RN-8 (editar validada)→400.

## Conformidad
- Arquitectura: RN en `services.py`; vistas delgadas; lecturas en `selectors.py`; permisos (`ActivityScope` + roles) y filtros presentes; router bajo `/api/v1/`. ✓
- Schema: campos de `TeachingActivity`/`ActivityValidation`/historial correctos; reutiliza módulos 1 y 2. ✓
- RN: 1, 2, 3/4, 5/6, 7, 8, 9 cubiertas por services + historiales + auditoría. ✓
- Convenciones de idioma. ✓

## Hallazgos
| # | Sev | Nota |
|---|-----|------|
| 1 | 🟡 baja | RN-10 (evidencia PDF) fuera de alcance del MVP — depende del repositorio externo de archivos (Fase 6). |
| 2 | 🟡 baja | `TutorViewSet`/validación: el rol `Tutor` que valida no se verifica que sea el tutor asignado a la actividad; aceptable MVP. |

## Resultado

**Módulo `actividades` aprobado y cerrado para el MVP.** Sin hallazgos altos/medios. Guía de pruebas en `spec/actividades.guia_pruebas.md`.
