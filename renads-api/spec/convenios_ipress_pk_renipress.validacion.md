# Validación — Refactor PK de `Ipress` (`codigo_renipress`)

Estado: **APROBADO** — el hallazgo ALTO A-1 (orden del grafo de migraciones) quedó **RESUELTO** en la re-validación. Sin hallazgos altos/medios pendientes. Se genera la guía de pruebas manuales (`spec/convenios_ipress_pk_renipress.guia_pruebas.md`).

Diagnóstico ejecutado en la re-validación (venv, solo lectura):
- `python manage.py showmigrations --plan` → orden correcto y sin ciclos (ver abajo).
- `python manage.py makemigrations --check --dry-run` → "No changes detected".
- `python manage.py check` → "System check identified no issues (0 silenced)".

---

## ALTO

### A-1 — Orden del plan de migraciones dejaba los backfills de `internados`/`actividades` DESPUÉS del drop de `Ipress.id` — **RESUELTO**

- **Ubicación del fix:** `apps/convenios/migrations/0047_ipress_pk_renipress_promote.py:50-54`.
- **Fix aplicado:** `0047` (que promueve `codigo_renipress` a PK y elimina `Ipress.id`) declara ahora `dependencies` cross-app sobre las dos migraciones transitorias con backfill:
  ```python
  dependencies = [
      ("convenios", "0046_ipress_pk_renipress_prep"),
      ("internados", "0021_ipress_codigo_transitorio"),
      ("actividades", "0006_ipress_codigo_transitorio"),
  ]
  ```
  Esto fuerza que ambos backfills corran **antes** del drop de `Ipress.id`. Se usó `dependencies` (aristas hacia migraciones anteriores) en lugar de `run_before` — equivalente en efecto y sin riesgo de invertir el sentido de la arista.
- **Verificación del orden (`showmigrations --plan`), sin ciclos:**
  `convenios/0046` → `internados/0021` → `actividades/0006` → `convenios/0047` → `actividades/0007` → `internados/0022`.
  (Django resolvió el grafo sin error; un ciclo habría hecho fallar `showmigrations`/`check`. Los `0022`/`0007` dependen de `0047` — aristas posteriores; la nueva arista de `0047` apunta solo a los transitorios `0021`/`0006` — anteriores. No hay back-edge → grafo acíclico.)
- **`0022`/`0007` dependen de `convenios/0047`:** confirmado — `internados/0022_ipress_fk_renipress.py:16-19` y `actividades/0007_ipress_fk_renipress.py:13-16` repuntan las FK reales tras la promoción del PK.
- **Los tres backfills leen el mapa `{ip.id: ip.codigo_renipress}` con el `id` aún existente:** confirmado — `convenios/0046:44`, `internados/0021:22`, `actividades/0006:16`; los tres se ejecutan antes del `RemoveField Ipress.id` de `0047` (paso A2).

---

## MEDIO

### M-1 — El backfill de convenios usa `ip.id` como clave del mapa — **SIN OBSERVACIÓN (era coherencia)**

- Confirmado tras el fix de A-1: los tres backfills (`0046`, `internados/0021`, `actividades/0006`) leen `ip.id` mientras la columna `id` de `ipress` aún existe (todos anteriores al drop de `0047`). El patrón es correcto y consistente. No bloqueante.

---

## Conforme (sin observaciones) — sin cambios respecto a la validación previa

El fix de A-1 tocó **solo** la lista `dependencies` de `0047` (grafo de migraciones); no altera modelos, operaciones de migración, código de aplicación ni docs. Se re-confirma que el resto sigue conforme:

- **T-02/T-04 (modelos):** `Ipress.codigo_renipress` PK texto sin `id`; `UserEntityProfile.id_objeto` / `AuditLog.id_objeto` → `CharField(64)`; los otros 4 GFK sin cambio.
- **T-03 (7 FK):** sin `to_field`; `db_column`, `related_name`, `on_delete` conservados.
- **T-05..T-10 (migraciones):** operaciones de campo en la app dueña; `RunPython` con `reverse_code=noop` y `RuntimeError` en español ante integridad rota; `db_column` finales canónicos (`ipress_id`, `ipress_origen_id`, `ipress_destino_id`).
- **T-11..T-18 (código de app):** selectores/permisos/views/serializers/filtros normalizados a `str` (universidades/propios casteados a `int` contra columnas enteras; `sedes`/`ipress_id` como `str`). `IpressViewSet.ordering = ["codigo_renipress"]`, `search_fields=["nombre","codigo_renipress"]`, `autorizar-sede-docente` intacta (`views.py:597-633`).
- **T-19..T-23 (docs):** los 4 `.md` de schema + `arquitectura_desarrollo.md` + `CLAUDE.md` sincronizados.

---

## Resultado

Validación **exitosa**. A-1 resuelto; sin bloqueantes altos/medios. `check` y `makemigrations --check` limpios. Guía de pruebas manuales generada en `spec/convenios_ipress_pk_renipress.guia_pruebas.md`.
