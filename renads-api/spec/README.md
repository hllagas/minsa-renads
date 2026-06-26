# spec/ — Tareas SDD por módulo

Carpeta de la metodología **Spec Driven Development**. Contiene, por cada módulo de RENADS:

- `convenios.md`, `internados.md`, `actividades.md` — lista exacta de tareas (la genera el agente **spec**).
- `<modulo>.validacion.md` — reporte de errores de validación (lo genera el agente **validator** solo si hay hallazgos).

Flujo: **Spec** crea las tareas → **Implement** las desarrolla en `apps/<modulo>/` → **Validator** revisa contra spec, arquitectura (`docs/arquitectura_desarrollo.md`) y schema (`docs/db_schema_*.md`). El **Orchestrator** coordina el ciclo. Ver `docs/alcance_mvp.md`.
