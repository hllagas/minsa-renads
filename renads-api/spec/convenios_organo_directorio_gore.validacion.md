# Validación — Refactor `gobierno_regional` a `convenio`

> Módulo: **Gestionar Convenios** (`apps/convenios`)
> Resultado: **APROBADO** — sin errores altos ni medios. Guía de pruebas generada en `convenios_organo_directorio_gore.guia_pruebas.md`.

## Resumen

Todos los ítems del checklist §9 del spec están implementados. `python manage.py check` → 0 issues; `makemigrations --check --dry-run` → "No changes detected".

| Ítem checklist §9 | Estado |
|---|---|
| `OrganDirectory` sin `gobierno_regional`; único constraint `(organo, nombre)` | OK (`models.py` L304-336) |
| `ExecutingUnit.gobierno_regional` intacto | OK (`models.py` L347-350) |
| `Convention.gobierno_regional` FK nullable PROTECT, `db_column`, help_text ES | OK (`models.py` L835-839) |
| Migración `0041` orden correcto (AddField→RunPython→RemoveConstraint×2→AddConstraint→RemoveField) | OK |
| Conteo GORE reportado; RunPython presente (real, con modelos históricos, reverse noop) | OK (3 órganos / 0 convenios documentado) |
| `makemigrations --check` limpio | OK |
| `_OrganDirectorySerializer` sin GORE; `validate()` por `(organo, nombre)`; 400 legible | OK (`views.py` L694-725) |
| `OrganDirectoryViewSet` sin GORE en filtros/detalles/`select_related` | OK (`views.py` L728-741) |
| `ConventionReadSerializer` expone `gobierno_regional` + `gobierno_regional_detalle` | OK (`serializers.py` L52,66,81-82) |
| `ConventionWriteSerializer` acepta `gobierno_regional` | OK (`serializers.py` L114) |
| `pdf._domicilio_entidad` GORE desde `convenio.gobierno_regional`; sin refs al órgano | OK (`pdf.py` L68-70) |
| `services.crear_adenda` hereda GORE | OK (`services.py` L358) |
| `crear_convenio`/`actualizar_convenio` persisten y validan por tipo; helper `_validar_gobierno_regional_por_tipo` | OK (`services.py` L154-179, 282-286, 303, 399-403) |
| `_validar_composicion_partes`/`sincronizar_partes` sin dependencia del GORE del órgano | OK |
| Grep global: cero refs vivas a `OrganDirectory.gobierno_regional` (fuera de migraciones) | OK (solo la nueva `0041` lo lee, antes del drop) |
| Docs sincronizadas (`db_schema_modulo_01_convenios.md`, `db_schema_er_global.md`, `CLAUDE.md`) | OK con una observación menor (ver abajo) |
| Idioma ES en tablas/columnas/help_text/mensajes; código en inglés | OK |

## Observaciones (baja severidad — no bloquean)

- **BAJA — `docs/db_schema_modulo_01_convenios.md` §12 "Mapa de relaciones" (bloque de texto ER, L687/L690/L716):** sigue reflejando las relaciones antiguas: `gobierno_regional ──< organo_directorio` (L687) y `organo_directorio (...) >── gobierno_regional (opcional, solo regionales)` (L690); y en L716 `convenio >── organo_directorio / universidad` no agrega `gobierno_regional`. El diagrama ER **global** (`db_schema_er_global.md`) sí quedó correcto; esta es una segunda representación ER dentro del doc de módulo que quedó desincronizada. Sugerencia: quitar L687, eliminar `>── gobierno_regional (opcional, solo regionales)` de L690 y añadir `convenio >── gobierno_regional (opcional, solo Marco regional)` en L716. (No enumerado explícitamente en la Tarea 7.2 del spec, que apuntaba solo al ER global.)

## Nota fuera de alcance (declarada por el usuario)

- El helper nuevo `services._validar_gobierno_regional_por_tipo` recibe `categoria_organo` derivado de `organo.categoria` (`crear_convenio` L250, reutilizado) y de `convenio.organo_directorio.categoria` (`actualizar_convenio` L401). El campo `categoria` de `OrganDirectory` fue retirado por la migración `0039` (reemplazado por el FK `organo`), por lo que ese acceso levantaría `AttributeError` en runtime. Es la **discrepancia pre-existente `organo_directorio.categoria`**, DECLARADA fuera del alcance de este refactor por el usuario. El helper solo replica el patrón ya presente en el código (`crear_convenio` ya usaba `organo.categoria` para la RN-1) y no introduce una clase nueva de fallo. Se menciona por completitud; **no** es un error de este refactor.
